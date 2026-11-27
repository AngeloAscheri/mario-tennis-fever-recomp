// SPIR-V rewrites of the translated shaders, split from vk_pipeline.c (see vk_spirv_patch.h).
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "vk.h"
#include "vk_spirv_patch.h"

// Binding decorations b >= 1 become b + off (the fragment stage's share of set 0).
uint32_t *spirv_rebind(const uint32_t *w, uint64_t n, uint32_t off) {
    uint32_t *o = malloc(n * 4);
    if (!o) return NULL;
    memcpy(o, w, n * 4);
    for (uint64_t i = 5; i < n;) {
        uint32_t op = o[i] & 0xffff, len = o[i] >> 16;
        if (!len || i + len > n) break;
        if (op == SPV_OP_DECORATE && len >= 4 && o[i + 2] == SPV_DEC_BINDING && o[i + 3] >= 1) o[i + 3] += off;
        i += len;
    }
    return o;
}

// DescriptorSet decorations become set (the fragment stage's resources move to set 1 with independent layouts).
uint32_t *spirv_set(const uint32_t *w, uint64_t n, uint32_t set) {
    uint32_t *o = malloc(n * 4);
    if (!o) return NULL;
    memcpy(o, w, n * 4);
    for (uint64_t i = 5; i < n;) {
        uint32_t op = o[i] & 0xffff, len = o[i] >> 16;
        if (!len || i + len > n) break;
        if (op == SPV_OP_DECORATE && len >= 4 && o[i + 2] == SPV_DEC_DESCRIPTOR_SET) o[i + 3] = set;
        i += len;
    }
    return o;
}

// Dual-source blending (docs/maxwell.md 5.6): SRC1 blend factors read the fragment shader's colour output 1,
// which Vulkan takes from Location 0, Index 1. The Output variable at Location 1 moves there, as Ryujinx declares it
// with DualSourceBlendEnable (CodeGen/Spirv/Declarations.cs); the pipeline is keyed by GKey.dsb, so only pipelines
// that blend with SRC1 get this module. NULL when the module has no Output at Location 1.
uint32_t *spirv_dual_source(const uint32_t *w, uint64_t n, uint64_t *out_n) {
    uint32_t outs[64];
    int nout = 0;
    uint64_t at = 0;
    for (uint64_t i = 5; i < n;) {
        uint32_t op = w[i] & 0xffff, len = w[i] >> 16;
        if (!len || i + len > n) return NULL;
        if (op == SPV_OP_VARIABLE && len >= 4 && w[i + 3] == SPV_SC_OUTPUT && nout < 64) outs[nout++] = w[i + 2];
        i += len;
    }
    for (uint64_t i = 5; i < n && !at;) {
        uint32_t op = w[i] & 0xffff, len = w[i] >> 16;
        if (op == SPV_OP_DECORATE && len == 4 && w[i + 2] == SPV_DEC_LOCATION && w[i + 3] == 1)
            for (int k = 0; k < nout; k++)
                if (outs[k] == w[i + 1]) at = i;
        i += len;
    }
    if (!at) return NULL;
    uint32_t *o = malloc((n + 4) * 4);
    if (!o) return NULL;
    memcpy(o, w, (at + 4) * 4);
    o[at + 3] = 0;
    o[at + 4] = 4u << 16 | SPV_OP_DECORATE, o[at + 5] = w[at + 1], o[at + 6] = SPV_DEC_INDEX, o[at + 7] = 1;
    memcpy(o + at + 8, w + at + 4, (n - at - 4) * 4);
    *out_n = n + 4;
    return o;
}

// Adds an Output variable for each Location of `missing` (type and width from io) to a module, declared in the entry
// point interface and initialised as Maxwell reads an unwritten output: (0, 0, 0, 1), the w as the bits of 1.0f whatever
// the type (attribute memory is untyped); fewer than 4 components are all zero. Existing scalar, vector and pointer types
// are reused. NULL when the module does not have the expected layout.
uint32_t *spirv_add_outputs(const uint32_t *w, uint64_t n, uint32_t missing, const GfxShaderIo io[32],
                            uint64_t *out_n) {
    uint64_t ep_at = 0, ann_end = 0, fn_at = 0;
    uint32_t bound = w[3], scalar[3] = {0, 0, 0};          // GFX_TYPE_FLOAT, SINT, UINT
    struct { uint32_t id, comp, count; } vec[64];
    struct { uint32_t id, type; } ptr[64];
    int nvec = 0, nptr = 0;
    for (uint64_t i = 5; i < n;) {
        uint32_t op = w[i] & 0xffff, len = w[i] >> 16;
        if (!len || i + len > n) return NULL;
        const uint32_t *a = w + i + 1;
        if (op == SPV_OP_ENTRY_POINT && !ep_at) ep_at = i;
        else if (op == SPV_OP_DECORATE || op == 72 || op == 73 || op == 74 || op == 75 || op == 332 || op == 5632 || op == 5633)
            ann_end = i + len;
        else if (op == SPV_OP_TYPE_FLOAT && len >= 3 && a[1] == 32) scalar[GFX_TYPE_FLOAT] = a[0];
        else if (op == SPV_OP_TYPE_INT && len >= 4 && a[1] == 32) scalar[a[2] ? GFX_TYPE_SINT : GFX_TYPE_UINT] = a[0];
        else if (op == SPV_OP_TYPE_VECTOR && len >= 4 && nvec < 64) vec[nvec].id = a[0], vec[nvec].comp = a[1], vec[nvec++].count = a[2];
        else if (op == SPV_OP_TYPE_POINTER && len >= 4 && a[1] == SPV_SC_OUTPUT && nptr < 64) ptr[nptr].id = a[0], ptr[nptr++].type = a[2];
        else if (op == SPV_OP_FUNCTION) { fn_at = i; break; }
        i += len;
    }
    if (!ep_at || !ann_end || !fn_at || ann_end < ep_at || fn_at < ann_end) return NULL;
    uint32_t types[32 * 40], decs[32 * 4], vars[32], zero[3] = {0, 0, 0}, one[3] = {0, 0, 0};
    int nt = 0, nd = 0, nv = 0;
    for (int l = 0; l < 32; l++) {
        if (!(missing >> l & 1)) continue;
        int t = io[l].type <= GFX_TYPE_UINT ? io[l].type : GFX_TYPE_FLOAT;
        uint32_t comps = io[l].comps ? io[l].comps : 4;
        if (!scalar[t]) {
            scalar[t] = bound++;
            if (t == GFX_TYPE_FLOAT) types[nt++] = 3u << 16 | SPV_OP_TYPE_FLOAT, types[nt++] = scalar[t], types[nt++] = 32;
            else types[nt++] = 4u << 16 | SPV_OP_TYPE_INT, types[nt++] = scalar[t], types[nt++] = 32, types[nt++] = t == GFX_TYPE_SINT;
        }
        uint32_t type = scalar[t];
        if (comps > 1) {
            int k = 0;
            while (k < nvec && !(vec[k].comp == type && vec[k].count == comps)) k++;
            if (k == nvec) {
                if (nvec == 64) return NULL;
                vec[nvec].id = bound++, vec[nvec].comp = type, vec[nvec++].count = comps;
                types[nt++] = 4u << 16 | SPV_OP_TYPE_VECTOR, types[nt++] = vec[k].id, types[nt++] = type, types[nt++] = comps;
            }
            type = vec[k].id;
        }
        int k = 0;
        while (k < nptr && ptr[k].type != type) k++;
        if (k == nptr) {
            if (nptr == 64) return NULL;
            ptr[nptr].id = bound++, ptr[nptr++].type = type;
            types[nt++] = 4u << 16 | SPV_OP_TYPE_POINTER, types[nt++] = ptr[k].id, types[nt++] = SPV_SC_OUTPUT, types[nt++] = type;
        }
        uint32_t init = bound++, var = bound++;
        if (comps == 4) {
            if (!zero[t]) {
                zero[t] = bound++, one[t] = bound++;
                types[nt++] = 4u << 16 | SPV_OP_CONSTANT, types[nt++] = scalar[t], types[nt++] = zero[t], types[nt++] = 0;
                types[nt++] = 4u << 16 | SPV_OP_CONSTANT, types[nt++] = scalar[t], types[nt++] = one[t], types[nt++] = 0x3f800000;
            }
            types[nt++] = 7u << 16 | SPV_OP_CONSTANT_COMPOSITE, types[nt++] = type, types[nt++] = init;
            types[nt++] = zero[t], types[nt++] = zero[t], types[nt++] = zero[t], types[nt++] = one[t];
        } else {
            types[nt++] = 3u << 16 | SPV_OP_CONSTANT_NULL, types[nt++] = type, types[nt++] = init;
        }
        types[nt++] = 5u << 16 | SPV_OP_VARIABLE, types[nt++] = ptr[k].id, types[nt++] = var, types[nt++] = SPV_SC_OUTPUT,
        types[nt++] = init;
        decs[nd++] = 4u << 16 | SPV_OP_DECORATE, decs[nd++] = var, decs[nd++] = SPV_DEC_LOCATION, decs[nd++] = (uint32_t)l;
        vars[nv++] = var;
    }
    uint64_t total = n + (uint64_t)(nt + nd + nv);
    uint32_t *o = malloc(total * 4), *p = o;
    if (!o) return NULL;
    uint32_t ep_len = w[ep_at] >> 16;
    memcpy(p, w, 5 * 4), p[3] = bound, p += 5;
    memcpy(p, w + 5, (ep_at - 5) * 4), p += ep_at - 5;
    *p++ = (ep_len + (uint32_t)nv) << 16 | SPV_OP_ENTRY_POINT;
    memcpy(p, w + ep_at + 1, (ep_len - 1) * 4), p += ep_len - 1;
    memcpy(p, vars, (size_t)nv * 4), p += nv;
    memcpy(p, w + ep_at + ep_len, (ann_end - ep_at - ep_len) * 4), p += ann_end - ep_at - ep_len;
    memcpy(p, decs, (size_t)nd * 4), p += nd;
    memcpy(p, w + ann_end, (fn_at - ann_end) * 4), p += fn_at - ann_end;
    memcpy(p, types, (size_t)nt * 4), p += nt;
    memcpy(p, w + fn_at, (n - fn_at) * 4), p += n - fn_at;
    *out_n = (uint64_t)(p - o);
    return o;
}

// Two fixes for what the translator declares but a shader does not use (NULL: nothing to change):
//  - the fragment shader interlock capability and extension, which Ryujinx adds to every fragment shader when the host
//    reports interlock support (SpirvGenerator.cs) and vk_device.c does not enable; kept when the shader interlocks;
//  - the CullDistance[1] member of gl_PerVertex next to ClipDistance[8] (Declarations.cs CreatePerVertexStructType):
//    9 distances exceed maxCombinedClipAndCullDistances (8 on the RX 9070). Ryujinx never accesses CullDistance; the
//    member goes when it is the struct's last and no access chain selects it.
uint32_t *spirv_fixup(const uint32_t *w, uint64_t n, uint64_t *out_n) {
    enum { OP_EXTENSION = 10, OP_CAPABILITY = 17, OP_MEMBER_NAME = 6, OP_EXECUTION_MODE = 16, OP_TYPE_ARRAY = 28,
           OP_TYPE_STRUCT = 30, OP_CONSTANT = 43, OP_MEMBER_DECORATE = 72, OP_ACCESS_CHAIN = 65, OP_IN_BOUNDS_ACCESS_CHAIN = 66,
           OP_BEGIN_INTERLOCK = 5364, OP_END_INTERLOCK = 5365, CAP_SAMPLE_INTERLOCK = 5363, CAP_PIXEL_INTERLOCK = 5378,
           CAP_RATE_INTERLOCK = 5372, BUILTIN_CLIP = 3, BUILTIN_CULL = 4 };
    if (n < 5) return NULL;
    uint32_t bound = w[3] < (1u << 22) ? w[3] : (1u << 22);
    uint32_t *val = calloc(bound, sizeof *val), *elem = calloc(bound, sizeof *elem), *len = calloc(bound, sizeof *len),
             *pointee = calloc(bound, sizeof *pointee), *var_type = calloc(bound, sizeof *var_type);
    uint32_t *o = NULL;
    int interlock_used = 0, interlock_declared = 0, cull_ok = 0;
    uint32_t cull_struct = 0, cull_member = 0, clip_member = ~0u, members = 0, member_types[8] = {0};
    if (!val || !elem || !len || !pointee || !var_type) goto out;
    for (uint64_t i = 5; i < n;) {
        uint32_t op = w[i] & 0xffff, l = w[i] >> 16;
        if (!l || i + l > n) goto out;
        const uint32_t *a = w + i + 1;
        if (op == OP_BEGIN_INTERLOCK || op == OP_END_INTERLOCK) interlock_used = 1;
        else if (op == OP_EXECUTION_MODE && l >= 3 && a[1] >= 5366 && a[1] <= 5371) interlock_used = 1;
        else if (op == OP_CAPABILITY && l >= 2 && (a[0] == CAP_PIXEL_INTERLOCK || a[0] == CAP_SAMPLE_INTERLOCK || a[0] == CAP_RATE_INTERLOCK))
            interlock_declared = 1;
        else if (op == OP_CONSTANT && l == 4 && a[1] < bound) val[a[1]] = a[2];
        else if (op == OP_TYPE_ARRAY && l >= 4 && a[0] < bound) elem[a[0]] = a[1], len[a[0]] = a[2] < bound ? val[a[2]] : 0;
        else if (op == SPV_OP_TYPE_POINTER && l >= 4 && a[0] < bound) pointee[a[0]] = a[2];
        else if (op == SPV_OP_VARIABLE && l >= 4 && a[1] < bound) var_type[a[1]] = a[0] < bound ? pointee[a[0]] : 0;
        else if (op == OP_MEMBER_DECORATE && l >= 5 && a[2] == SPV_DEC_BUILTIN && a[3] == BUILTIN_CULL) cull_struct = a[0], cull_member = a[1];
        else if (op == OP_MEMBER_DECORATE && l >= 5 && a[2] == SPV_DEC_BUILTIN && a[3] == BUILTIN_CLIP) clip_member = a[1];
        else if (op == OP_TYPE_STRUCT && cull_struct && a[0] == cull_struct && l >= 2) {
            members = l - 2;
            for (uint32_t m = 0; m < members && m < 8; m++) member_types[m] = a[1 + m];
        } else if ((op == OP_ACCESS_CHAIN || op == OP_IN_BOUNDS_ACCESS_CHAIN) && l >= 5 && cull_struct && a[2] < bound) {
            uint32_t t = var_type[a[2]], k = 3;
            if (t < bound && t && elem[t] == cull_struct) k = 4;   // arrayed per-vertex block
            if ((t == cull_struct || k == 4) && k + 1 < l && a[k] < bound && val[a[k]] == cull_member) cull_struct = 0;
        }
        i += l;
    }
    VkCtx *c = vk_ctx();
    uint32_t limit = c ? c->props.limits.maxCombinedClipAndCullDistances : 8;
    if (cull_struct && members && members <= 8 && cull_member == members - 1 && clip_member < members) {
        uint32_t clip_t = member_types[clip_member], cull_t = member_types[cull_member];
        uint32_t clip_n = clip_t < bound ? len[clip_t] : 0, cull_n = cull_t < bound ? len[cull_t] : 0;
        cull_ok = clip_n + cull_n > limit && clip_n <= limit;
    }
    int strip = interlock_declared && !interlock_used;
    if (!strip && !cull_ok) goto out;
    o = malloc(n * 4);
    if (!o) goto out;
    uint64_t on = 5;
    memcpy(o, w, 5 * 4);
    for (uint64_t i = 5; i < n;) {
        uint32_t op = w[i] & 0xffff, l = w[i] >> 16;
        const uint32_t *a = w + i + 1;
        int drop = 0;
        if (strip && op == OP_CAPABILITY && (a[0] == CAP_PIXEL_INTERLOCK || a[0] == CAP_SAMPLE_INTERLOCK || a[0] == CAP_RATE_INTERLOCK)) drop = 1;
        if (strip && op == OP_EXTENSION && l >= 2 && !strncmp((const char *)a, "SPV_EXT_fragment_shader_interlock", (l - 1) * 4)) drop = 1;
        if (cull_ok && (op == OP_MEMBER_DECORATE || op == OP_MEMBER_NAME) && l >= 3 && a[0] == cull_struct && a[1] == cull_member) drop = 1;
        if (!drop) {
            memcpy(o + on, w + i, l * 4);
            if (cull_ok && op == OP_TYPE_STRUCT && a[0] == cull_struct) o[on] = (l - 1) << 16 | op;   // last member gone
            on += op == OP_TYPE_STRUCT && cull_ok && a[0] == cull_struct ? l - 1 : l;
        }
        i += l;
    }
    *out_n = on;
out:
    free(val), free(elem), free(len), free(pointee), free(var_type);
    return o;
}

// True when the module declares a GroupNonUniform* or SubgroupBallot-style capability (lane masks assume 32 lanes).
int uses_subgroup_ops(const uint32_t *w, uint64_t words) {
    for (uint64_t i = 5; i < words;) {
        uint32_t op = w[i] & 0xffff, n = w[i] >> 16;
        if (!n || i + n > words) return 0;
        if (op != 17) return 0;   // OpCapability; capabilities come first, stop at the first other instruction
        uint32_t cap = w[i + 1];
        if ((cap >= 61 && cap <= 68) || cap == 4423 || cap == 4431) return 1;   // NonUniform*, SubgroupBallotKHR, SubgroupVoteKHR
        i += n;
    }
    return 0;
}

// Workgroup memory against the device's maxComputeSharedMemorySize, for the translator's smem (the largest workgroup
// uint array, sized from the program's control section). MKW declares 48 KiB in 168 compute programs; Adreno 7xx has
// 32 KiB, and Turnip's compiler ends the process on such a shader (ir3.c ir3_get_reg_independent_max_waves: no workgroup
// fits, "impossible to have enough concurrent waves", exit(1)), so the array is cut to fit. The 168 index smem by the
// thread's global index (gl_WorkGroupID.x * 64 + local, times 48 bytes, up to 1024 items): every workgroup past the 10th
// reached past the cut end, into other workgroups' memory on Adreno (flashing blue vertical lines in races, Odin 2).
// The translator indexes an array over 32 KiB modulo SMEM_WRAP, a constant with a sentinel value, rewritten here in
// every module that has it: to the words kept where the array is cut (each workgroup's 3 KiB window then wraps inside
// it), else to the next power of two at least the array's words, a no-op modulo the compiler turns into a mask.
// NULL when nothing changes or the layout is not the translator's; *from / *to: the bytes declared and kept.
#define SMEM_WRAP_SENTINEL 0x7ffe5a3bu

uint32_t *spirv_clamp_shared(const uint32_t *w, uint64_t n, uint32_t limit, uint64_t *out_n, uint32_t *from,
                             uint32_t *to) {
    enum { OP_TYPE_BOOL = 20, OP_TYPE_ARRAY = 28, OP_TYPE_STRUCT = 30, SC_WORKGROUP = 4 };
    if (n < 5 || !limit) return NULL;
    uint32_t bound = w[3];
    if (bound >= (1u << 22)) return NULL;
    uint64_t *size = calloc(bound, sizeof *size);
    uint32_t *val = calloc(bound, sizeof *val), *arr_elem = calloc(bound, sizeof *arr_elem),
             *ptr_to = calloc(bound, sizeof *ptr_to);
    uint8_t *is_u32 = calloc(bound, 1), *other_ptr = calloc(bound, 1);
    uint32_t *o = NULL, wg_vars[16], nwg = 0, sentinel = 0;
    if (!size || !val || !arr_elem || !ptr_to || !is_u32 || !other_ptr) goto out;
    for (uint64_t i = 5; i < n;) {
        uint32_t op = w[i] & 0xffff, l = w[i] >> 16;
        if (!l || i + l > n) goto out;
        const uint32_t *a = w + i + 1;
        if (op == SPV_OP_FUNCTION) break;
        if ((op == SPV_OP_TYPE_INT || op == SPV_OP_TYPE_FLOAT) && l >= 3 && a[0] < bound) {
            size[a[0]] = a[1] / 8;
            is_u32[a[0]] = op == SPV_OP_TYPE_INT && a[1] == 32;
        } else if (op == OP_TYPE_BOOL && l >= 2 && a[0] < bound) size[a[0]] = 4;
        else if (op == SPV_OP_TYPE_VECTOR && l >= 4 && a[0] < bound && a[1] < bound) size[a[0]] = size[a[1]] * a[2];
        else if (op == SPV_OP_CONSTANT && l == 4 && a[1] < bound) {
            val[a[1]] = a[2];
            sentinel |= a[2] == SMEM_WRAP_SENTINEL;
        }
        else if (op == OP_TYPE_ARRAY && l >= 4 && a[0] < bound && a[1] < bound && a[2] < bound) {
            arr_elem[a[0]] = a[1];
            size[a[0]] = size[a[1]] * val[a[2]];
        } else if (op == OP_TYPE_STRUCT && l >= 2 && a[0] < bound) {
            for (uint32_t m = 1; m + 1 < l; m++) size[a[0]] += a[m] < bound ? size[a[m]] : 0;
        } else if (op == SPV_OP_TYPE_POINTER && l >= 4 && a[0] < bound && a[2] < bound) {
            ptr_to[a[0]] = a[2];
            if (a[1] != SC_WORKGROUP) other_ptr[a[2]] = 1;
        } else if (op == SPV_OP_VARIABLE && l >= 4 && a[2] == SC_WORKGROUP && a[0] < bound && nwg < 16) {
            wg_vars[nwg++] = ptr_to[a[0]];
        }
        i += l;
    }
    uint64_t total = 0;
    uint32_t big = 0;
    for (uint32_t k = 0; k < nwg; k++) {
        total += size[wg_vars[k]];
        uint32_t t = wg_vars[k];
        if (t && arr_elem[t] && is_u32[arr_elem[t]] && !other_ptr[t] && (!big || size[t] > size[big])) big = t;
    }
    int cut = total > limit && big && total - size[big] < limit;
    if (!cut && !sentinel) goto out;
    uint32_t keep = cut ? (uint32_t)((limit - (total - size[big])) / 4) : 0, wrap = big ? 1 : 0x80000000u;
    if (cut) wrap = keep;
    else
        while (wrap < size[big] / 4 && wrap < 0x80000000u) wrap <<= 1;
    o = malloc((n + 4) * 4);
    if (!o) goto out;
    memcpy(o, w, 5 * 4);
    o[3] = cut ? bound + 1 : bound;
    uint64_t on = 5;
    for (uint64_t i = 5; i < n;) {
        uint32_t op = w[i] & 0xffff, l = w[i] >> 16;
        if (cut && op == OP_TYPE_ARRAY && w[i + 1] == big) {
            o[on++] = 4u << 16 | SPV_OP_CONSTANT, o[on++] = arr_elem[big], o[on++] = bound, o[on++] = keep;
            memcpy(o + on, w + i, l * 4);
            o[on + 3] = bound;
        } else if (op == SPV_OP_CONSTANT && l == 4 && w[i + 1] < bound && is_u32[w[i + 1]] &&
                   w[i + 3] == SMEM_WRAP_SENTINEL) {
            memcpy(o + on, w + i, l * 4);   // glsl/common.py SMEM_WRAP_SENTINEL
            o[on + 3] = wrap;
        } else {
            memcpy(o + on, w + i, l * 4);
        }
        on += l;
        i += l;
    }
    *out_n = on;
    *from = (uint32_t)total, *to = cut ? (uint32_t)(total - size[big] + (uint64_t)keep * 4) : (uint32_t)total;
out:
    free(size), free(val), free(arr_elem), free(ptr_to), free(is_u32), free(other_ptr);
    return o;
}

// ---- passthrough geometry stage (mtf-recomp)
// The translator writes one module per passthrough geometry program, for triangles and every attribute Location
// (sm86/translate/glsl/head.py gs_head, gs_main): main() copies in_attr<L>[v] to out_attr<L> for each vertex v < GS_NV.
// A pipeline gets it adapted to its vertex stage and topology:
//  - topology class 0 points, 1 lines, 2 triangles: the input and output execution modes, OutputVertices, the length of
//    the per-vertex Input arrays and GS_NV become 1, 2 or 3;
//  - GS_CLIP becomes the clip distances the vertex stage writes, and the input gl_PerVertex block gets the members of
//    the vertex module's output block (ClipDistance's length, CullDistance), as interface matching requires;
//  - every Input and Output variable at a Location outside keep (what the vertex stage writes: Vulkan requires each
//    input of a stage to be written by the one before) goes, with its name and decorations, its entry in the interface,
//    and the access chains, loads and stores that use it. Any other use of such a variable fails the rewrite.
// NULL when the module is not in that form (logged by the caller).
enum { GS_OP_NAME = 5, GS_OP_EXECUTION_MODE = 16, GS_OP_TYPE_ARRAY = 28, GS_OP_TYPE_STRUCT = 30, GS_OP_SPEC_CONSTANT = 50,
       GS_OP_LOAD = 61, GS_OP_STORE = 62, GS_OP_COPY_MEMORY = 63, GS_OP_ACCESS_CHAIN = 65, GS_OP_IN_BOUNDS_ACCESS_CHAIN = 66,
       GS_OP_MEMBER_NAME = 6, GS_OP_MEMBER_DECORATE = 72, GS_DEC_SPEC_ID = 1, GS_SC_INPUT = 1,
       GS_EM_INPUT_POINTS = 19, GS_EM_INPUT_LINES = 20, GS_EM_TRIANGLES = 22, GS_EM_OUTPUT_VERTICES = 26,
       GS_EM_OUTPUT_POINTS = 27, GS_EM_OUTPUT_LINE_STRIP = 28, GS_EM_OUTPUT_TRIANGLE_STRIP = 29 };

// The vertex module's output gl_PerVertex block (glslang's: Position, PointSize, ClipDistance, CullDistance): the
// length of its ClipDistance array and of its CullDistance array (0: no such member). 0 when it has no such block.
int spirv_vs_block(const uint32_t *w, uint64_t n, uint32_t *clip_len, uint32_t *cull_len) {
    uint32_t bound = n >= 5 ? w[3] : 0, st = 0, kc = ~0u, kd = ~0u;
    *clip_len = *cull_len = 0;
    if (!bound) return 0;
    for (uint64_t i = 5; i < n; i += w[i] >> 16) {   // the struct whose members are ClipDistance and CullDistance
        uint32_t op = w[i] & 0xffff, len = w[i] >> 16;
        if (!len || i + len > n) return 0;
        if (op == GS_OP_MEMBER_DECORATE && len >= 5 && w[i + 3] == SPV_DEC_BUILTIN && (w[i + 4] == 3 || w[i + 4] == 4)) {
            if (st && st != w[i + 1]) return 0;   // two blocks: not a vertex module's
            st = w[i + 1];
            if (w[i + 4] == 3) kc = w[i + 2];
            else kd = w[i + 2];
        }
    }
    if (!st || kc == ~0u) return 0;
    uint32_t tc = 0, td = 0;
    for (uint64_t i = 5; i < n; i += w[i] >> 16)
        if ((w[i] & 0xffff) == GS_OP_TYPE_STRUCT && w[i + 1] == st) {
            uint32_t len = w[i] >> 16;
            if (kc + 2 < len) tc = w[i + 2 + kc];
            if (kd != ~0u && kd + 2 < len) td = w[i + 2 + kd];
        }
    uint32_t lc = 0, ld = 0;   // the arrays' length constants
    for (uint64_t i = 5; i < n; i += w[i] >> 16)
        if ((w[i] & 0xffff) == GS_OP_TYPE_ARRAY && (w[i] >> 16) >= 4) {
            if (w[i + 1] == tc) lc = w[i + 3];
            if (td && w[i + 1] == td) ld = w[i + 3];
        }
    for (uint64_t i = 5; i < n; i += w[i] >> 16)
        if ((w[i] & 0xffff) == SPV_OP_CONSTANT && (w[i] >> 16) >= 4) {
            if (lc && w[i + 2] == lc) *clip_len = w[i + 3];
            if (ld && w[i + 2] == ld) *cull_len = w[i + 3];
        }
    return *clip_len >= 1 && *clip_len <= 8 && (!td || (*cull_len >= 1 && *cull_len <= 8));
}

uint32_t *spirv_gs_adapt(const uint32_t *w, uint64_t n, int topo_class, uint32_t keep, int clip, uint32_t vs_clip_len,
                         uint32_t vs_cull_len, uint64_t *out_n) {
    if (n < 5 || topo_class < 0 || topo_class > 2 || clip < 0 || clip > 8 || vs_clip_len < 1 || vs_clip_len > 8 ||
        vs_cull_len > 8)
        return NULL;
    uint32_t bound = w[3], nv = (uint32_t)topo_class + 1;
    uint32_t blk = 0, blk_clip = ~0u, f32 = 0, u32 = 0;   // the input gl_PerVertex, its ClipDistance member, float, uint
    uint8_t *drop = calloc(bound + 1, 1), *in_arr = calloc(bound + 1, 1), *bad_arr = calloc(bound + 1, 1);
    int32_t *loc = calloc(bound + 1, sizeof *loc);
    uint32_t *ptr_sc = calloc(bound + 1, sizeof *ptr_sc), *ptr_to = calloc(bound + 1, sizeof *ptr_to);
    uint32_t *o = malloc((n + 32) * 4);
    uint32_t nv_id = 0, clip_id = 0, new_len = 0, len_type = 0;
    uint64_t at = 0;
    if (!drop || !in_arr || !bad_arr || !loc || !ptr_sc || !ptr_to || !o) goto fail;
    // pass 1: Locations, spec ids, pointers, and the variables to drop
    for (uint64_t i = 5; i < n;) {
        uint32_t op = w[i] & 0xffff, len = w[i] >> 16;
        if (!len || i + len > n) goto fail;
        const uint32_t *a = w + i + 1;
        if (op == SPV_OP_DECORATE && len >= 4 && a[0] < bound) {
            if (a[1] == SPV_DEC_LOCATION) loc[a[0]] = (int32_t)a[2] + 1;
            else if (a[1] == GS_DEC_SPEC_ID && a[2] == 4000) nv_id = a[0];   // GS_NV (head.py GS_NV_ID)
            else if (a[1] == GS_DEC_SPEC_ID && a[2] == 4001) clip_id = a[0];   // GS_CLIP
        } else if (op == SPV_OP_TYPE_POINTER && len >= 4 && a[0] < bound) {
            ptr_sc[a[0]] = a[1], ptr_to[a[0]] = a[2];
        } else if (op == SPV_OP_VARIABLE && len >= 4 && a[1] < bound && a[0] < bound) {
            uint32_t sc = a[2], l = loc[a[1]];
            if ((sc == GS_SC_INPUT || sc == SPV_SC_OUTPUT) && l > 0 && !(keep >> (l - 1) & 1)) drop[a[1]] = 1;
            else if (sc == GS_SC_INPUT && ptr_to[a[0]] < bound) in_arr[ptr_to[a[0]]] = 1;   // a kept per-vertex input
        }
        i += len;
    }
    if (!nv_id || !clip_id) goto fail;   // not the translator's passthrough module
    // the input block: the element of a per-vertex Input array that carries BuiltIn members; float and uint from its
    // ClipDistance array (float[8]: its element and its length's type)
    for (uint64_t i = 5; i < n && !blk; i += w[i] >> 16)
        if ((w[i] & 0xffff) == GS_OP_TYPE_ARRAY && (w[i] >> 16) >= 4 && w[i + 1] < bound && in_arr[w[i + 1]])
            for (uint64_t j = 5; j < n; j += w[j] >> 16)
                if ((w[j] & 0xffff) == GS_OP_MEMBER_DECORATE && (w[j] >> 16) >= 5 && w[j + 1] == w[i + 2] &&
                    w[j + 3] == SPV_DEC_BUILTIN) {
                    blk = w[i + 2];
                    if (w[j + 4] == 3) blk_clip = w[j + 2];
                }
    for (uint64_t j = 5; blk && j < n; j += w[j] >> 16)   // its ClipDistance member's index
        if ((w[j] & 0xffff) == GS_OP_MEMBER_DECORATE && (w[j] >> 16) >= 5 && w[j + 1] == blk && w[j + 3] == SPV_DEC_BUILTIN &&
            w[j + 4] == 3)
            blk_clip = w[j + 2];
    if (!blk || blk_clip == ~0u) goto fail;
    for (uint64_t i = 5; i < n; i += w[i] >> 16)
        if ((w[i] & 0xffff) == GS_OP_TYPE_STRUCT && w[i + 1] == blk && blk_clip + 2 < (w[i] >> 16)) {
            uint32_t arr = w[i + 2 + blk_clip];
            for (uint64_t j = 5; j < i; j += w[j] >> 16)
                if ((w[j] & 0xffff) == GS_OP_TYPE_ARRAY && w[j + 1] == arr) {
                    f32 = w[j + 2];
                    for (uint64_t k = 5; k < j; k += w[k] >> 16)
                        if ((w[k] & 0xffff) == SPV_OP_CONSTANT && w[k + 2] == w[j + 3]) u32 = w[k + 1];
                }
        }
    if (!f32 || !u32) goto fail;
    // array types other than per-vertex inputs must keep their length
    for (uint64_t i = 5; i < n; i += w[i] >> 16) {
        uint32_t op = w[i] & 0xffff, len = w[i] >> 16;
        const uint32_t *a = w + i + 1;
        if (op == SPV_OP_TYPE_POINTER && len >= 4 && a[1] != GS_SC_INPUT && a[2] < bound) bad_arr[a[2]] = 1;
        else if (op == GS_OP_TYPE_STRUCT)
            for (uint32_t k = 1; k + 1 < len; k++)
                if (a[k] < bound) bad_arr[a[k]] = 1;
    }
    // pass 2: the rewrite
    memcpy(o, w, 5 * 4);
    at = 5;
    int in_fn = 0;
    for (uint64_t i = 5; i < n;) {
        uint32_t op = w[i] & 0xffff, len = w[i] >> 16;
        const uint32_t *a = w + i + 1;
        int keep_insn = 1;
        if (op == SPV_OP_FUNCTION) in_fn = 1;
        if (op == SPV_OP_ENTRY_POINT) {
            uint32_t k = 2;   // the name, a NUL-terminated string in words
            while (k < len - 1 && (a[k] >> 24)) k++;
            k++;
            uint64_t start = at;
            for (uint32_t j = 0; j < k && j + 1 < len; j++) o[at + 1 + j] = a[j];
            at += 1 + k;
            for (uint32_t j = k; j + 1 < len; j++)
                if (a[j] >= bound || !drop[a[j]]) o[at++] = a[j];
            o[start] = (uint32_t)(at - start) << 16 | op;
            i += len;
            continue;
        }
        if ((op == GS_OP_NAME || op == GS_OP_MEMBER_NAME || op == SPV_OP_DECORATE) && len >= 2 && a[0] < bound && drop[a[0]])
            keep_insn = 0;
        else if (op == GS_OP_MEMBER_DECORATE && len >= 5 && a[0] == blk && a[1] == blk_clip && a[2] == SPV_DEC_BUILTIN) {
            memcpy(o + at, w + i, len * 4), at += len;   // the vertex block's CullDistance follows its ClipDistance
            if (vs_cull_len) o[at++] = 5u << 16 | GS_OP_MEMBER_DECORATE, o[at++] = blk, o[at++] = blk_clip + 1,
                             o[at++] = SPV_DEC_BUILTIN, o[at++] = 4;
            i += len;
            continue;
        } else if (op == GS_OP_TYPE_STRUCT && len >= 2 && a[0] == blk) {
            if (blk_clip + 3 != len) goto fail;   // ClipDistance must be its last member, as the translator writes it
            uint32_t lc = bound++, ac = bound++;
            o[at++] = 4u << 16 | SPV_OP_CONSTANT, o[at++] = u32, o[at++] = lc, o[at++] = vs_clip_len;
            o[at++] = 4u << 16 | GS_OP_TYPE_ARRAY, o[at++] = ac, o[at++] = f32, o[at++] = lc;
            uint32_t ad = 0;
            if (vs_cull_len) {
                uint32_t ld = bound++;
                ad = bound++;
                o[at++] = 4u << 16 | SPV_OP_CONSTANT, o[at++] = u32, o[at++] = ld, o[at++] = vs_cull_len;
                o[at++] = 4u << 16 | GS_OP_TYPE_ARRAY, o[at++] = ad, o[at++] = f32, o[at++] = ld;
            }
            o[at++] = (len + (ad ? 1u : 0u)) << 16 | op;
            for (uint32_t k = 0; k + 1 < len; k++) o[at++] = k == blk_clip + 1 ? ac : a[k];
            if (ad) o[at++] = ad;
            i += len;
            continue;
        }
        else if (op == GS_OP_EXECUTION_MODE && len >= 3 && topo_class != 2) {
            uint32_t m = a[1];
            static const uint32_t in_mode[3] = {GS_EM_INPUT_POINTS, GS_EM_INPUT_LINES, GS_EM_TRIANGLES};
            static const uint32_t out_mode[3] = {GS_EM_OUTPUT_POINTS, GS_EM_OUTPUT_LINE_STRIP, GS_EM_OUTPUT_TRIANGLE_STRIP};
            memcpy(o + at, w + i, len * 4);
            if (m == GS_EM_TRIANGLES) o[at + 2] = in_mode[topo_class];
            else if (m == GS_EM_OUTPUT_TRIANGLE_STRIP) o[at + 2] = out_mode[topo_class];
            else if (m == GS_EM_OUTPUT_VERTICES && len >= 4) o[at + 3] = nv;
            at += len, i += len;
            continue;
        } else if (op == GS_OP_TYPE_ARRAY && len >= 4 && topo_class != 2 && a[0] < bound && in_arr[a[0]]) {
            if (bad_arr[a[0]]) goto fail;   // shared with something that is not a per-vertex input
            if (!new_len) {   // the new length, declared before its first use with the old length's type
                len_type = 0;
                for (uint64_t j = 5; j < i; j += w[j] >> 16)
                    if ((w[j] & 0xffff) == SPV_OP_CONSTANT && (w[j] >> 16) >= 4 && w[j + 2] == a[2]) len_type = w[j + 1];
                if (!len_type) goto fail;
                new_len = bound++;
                o[at++] = 4u << 16 | SPV_OP_CONSTANT, o[at++] = len_type, o[at++] = new_len, o[at++] = nv;
            }
            o[at++] = w[i], o[at++] = a[0], o[at++] = a[1], o[at++] = new_len;
            i += len;
            continue;
        } else if (op == GS_OP_SPEC_CONSTANT && len >= 4 && (a[1] == nv_id || a[1] == clip_id)) {
            memcpy(o + at, w + i, len * 4);
            o[at + 3] = a[1] == nv_id ? nv : (uint32_t)clip;
            at += len, i += len;
            continue;
        } else if (op == SPV_OP_VARIABLE && len >= 4 && a[1] < bound && drop[a[1]]) {
            keep_insn = 0;
        } else if ((op == GS_OP_ACCESS_CHAIN || op == GS_OP_IN_BOUNDS_ACCESS_CHAIN) && len >= 4 && a[2] < bound && drop[a[2]]) {
            if (a[1] < bound) drop[a[1]] = 1;
            keep_insn = 0;
        } else if (op == GS_OP_LOAD && len >= 4 && a[2] < bound && drop[a[2]]) {
            if (a[1] < bound) drop[a[1]] = 1;
            keep_insn = 0;
        } else if ((op == GS_OP_STORE || op == GS_OP_COPY_MEMORY) && len >= 3 &&
                   ((a[0] < bound && drop[a[0]]) || (a[1] < bound && drop[a[1]]))) {
            keep_insn = 0;
        } else if (in_fn) {   // any other use of a dropped id in a function: not the expected form
            for (uint32_t k = 0; k + 1 < len; k++)
                if (a[k] < bound && drop[a[k]]) goto fail;
        }
        if (keep_insn) memcpy(o + at, w + i, len * 4), at += len;
        i += len;
    }
    o[3] = bound;
    free(drop), free(in_arr), free(bad_arr), free(loc), free(ptr_sc), free(ptr_to);
    *out_n = at;
    return o;
fail:
    free(drop), free(in_arr), free(bad_arr), free(loc), free(ptr_sc), free(ptr_to), free(o);
    return NULL;
}

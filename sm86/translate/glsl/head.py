"""SM86 -> GLSL: the declarations before main() (version, extensions, helper functions, inputs and outputs,
resource bindings and their reflection) and the task/mesh wrappers around the translated body."""

from glsl.common import (HMMA_FN, LDSM_FN, LOP3_FN, MOVM_FN, NMINMAX_FN, PRMT_FN, SHFL_FN, SMEM_PORTABLE_WORDS,
                         SMEM_WRAP_SENTINEL, WARP_FN, Unsupported)  # fmt: skip
from glsl.thread import ThreadOps


def interp(b, stage: str, attr: int) -> str:
    """A PS input's interpolation from the SPH input map, as eden-nx2 translate_program.cpp:78-87: constant -> flat,
    screen linear -> noperspective. Declared smooth, the flat inputs that carry integers as float bits (the race
    bushes' material index in in_attr1.w) were interpolated and broke (01/11/2026); a component mix never occurs (census
    of the 7 262 PS: 992 flat, 2 439 linear attributes)."""
    if stage != "ps" or not b.sph:
        return ""
    byte = (b.sph.words[6 + (attr >> 2)] >> ((attr & 3) * 8)) & 0xFF
    modes = {(byte >> (k * 2)) & 3 for k in range(4)} - {0}
    return {1: "flat ", 3: "noperspective "}.get(modes.pop(), "") if len(modes) == 1 else ""

def sampler_type(glsl_type: str) -> int:
    """Ryujinx SamplerType (gfx_shader.c GfxShaderRes.type): 1 1D, 3 2D, 4 3D, 5 cube | 0x100 array, 0x200
    multisample, 0x400 shadow."""
    base = glsl_type.removeprefix("sampler").removeprefix("u").removeprefix("image")
    ms = "MS" in base
    code = {"1D": 1, "2D": 3, "3D": 4, "Cube": 5}[base.removesuffix("Shadow").removesuffix("Array").replace("MS", "")]
    return code | (0x100 if "Array" in base else 0) | (0x200 if ms else 0) | (0x400 if base.endswith("Shadow") else 0)


def declarations(b, stage: str, shape: tuple[int, int, int, int] | None) -> list[str]:
    """Lines before main() for Builder b once the body is translated; sets b.reflection."""
    head = [
        "#version 460",
        "#extension GL_ARB_gpu_shader_int64 : require",
        # jumps or loop passes before giving up: a wrong loop must not hang the GPU. Graphics stages run per pixel or
        # vertex, so their cap is lower: 65536 passes in every pixel of a 1280x720 target take the GPU past amdgpu's
        # timeout (run93 reset the GPU, cause not pinned down; 4096 is a safety bound, not a measured need)
        f"#define LOOP_CAP {'0x10000u' if stage == 'cs' else '0x1000u'}",
    ]
    if b.uses_subgroup:
        head += [
            "#extension GL_KHR_shader_subgroup_basic : require",
            "#extension GL_KHR_shader_subgroup_ballot : require",
            "#extension GL_KHR_shader_subgroup_vote : require",
            "#extension GL_KHR_shader_subgroup_shuffle : require",
        ]
        if b.uses_arith:
            head.append("#extension GL_KHR_shader_subgroup_arithmetic : require")  # fmt: skip
        head.append(WARP_FN)
    if stage == "cs":
        # Workgroup and shared memory size from the program's control section (compute_shape). They were
        # specialization constants that no back end set: every dispatch ran 1x1x1 groups until 31/10/2026.
        x, y, z, _ = shape or (1, 1, 1, 0)
        head += [f"layout(local_size_x = {x}, local_size_y = {y}, local_size_z = {z}) in;"]
    if b.uses_shared:
        words = (shape[3] + 3) // 4 if shape and shape[3] else 16384
        head += [f"const uint SMEM_WORDS = {words}u;", "shared uint smem[SMEM_WORDS];"]
        if words > SMEM_PORTABLE_WORDS:
            # Over 32 KiB, more than some GPUs have (Adreno): the runtime cuts smem there and sets SMEM_WRAP (a
            # sentinel constant it looks for) to the words kept, so each workgroup's window wraps inside the cut array
            # instead of reaching past it; where the array fits it sets a power of two, a mask after compilation
            # (vk_spirv_patch.c spirv_clamp_shared).
            head += [f"const uint SMEM_WRAP = {SMEM_WRAP_SENTINEL:#x}u;", "#define SMEM(i) smem[(i) % SMEM_WRAP]"]
        else:
            head.append("#define SMEM(i) smem[i]")
        if b.uses_ldsm:
            head.append(LDSM_FN)
    if b.uses_hmma:
        head.append(HMMA_FN)
    if b.uses_movm:
        head.append(MOVM_FN)
    if b.lmem_bytes:
        sph_bytes = b.sph.words[1] & 0xFFFFFF if b.sph else 0
        head += [f"const uint LMEM_WORDS = {(max(b.lmem_bytes, sph_bytes) + 3) // 4}u;", "uint lmem[LMEM_WORDS];"]
    if b.uses_lop3:
        head.append(LOP3_FN)
    if b.uses_shfl:
        head.append(SHFL_FN)
    if b.uses_prmt:
        head.append(PRMT_FN)
    if getattr(b, "uses_nminmax", False):
        head.insert(2, "#extension GL_EXT_spirv_intrinsics : require")
        head.append(NMINMAX_FN)
    if b.images:
        head.insert(2, "#extension GL_EXT_shader_image_load_formatted : require")
    if b.uses_shadow_lod:
        head.insert(2, "#extension GL_EXT_texture_shadow_lod : require")
    if getattr(b, "uses_demote", False):
        head.insert(2, "#extension GL_EXT_demote_to_helper_invocation : require")
    if getattr(b, "vtg", False):
        head += vtg_head(b)
    elif stage == "gs":
        head += gs_head(b)
    if not getattr(b, "vtg", False):
        head += [f"layout(location = {a}) {interp(b, stage, a)}in vec4 in_attr{a};" for a in sorted(b.in_attrs)]
    if getattr(b, "vtg", False):
        pass   # vtg_head declared the outputs
    elif stage == "ps":
        head += [f"layout(location = {t}) out vec4 out_color{t};" for t in sorted(b.out_attrs)]
    else:
        head += [f"layout(location = {t}) out vec4 out_attr{t};" for t in sorted(b.out_attrs)]
        if getattr(b, "clip", 0):
            head.append(f"out float gl_ClipDistance[{b.clip}];")
        if stage == "vs" and not (b.task or b.mesh):
            # NVN's point size (SetPointSize) for the programs that write none; Vulkan leaves gl_PointSize undefined on
            # point lists (VUID topology-08773). Ryujinx's SupportBuffer.PointSize (MIT); the back end fills it.
            head.append("layout(std140, binding = 0) uniform Support { vec4 pad[87]; float point_size; } support;")
    # Bindings from 1 (0 is the back end's support buffer), set 0, in this order: constant banks, storage buffers,
    # textures, images; the reflection names each the way runtime/gfx/nvn/host/gfx_shader.c add_res() reads it.
    refl: dict = {"stage": "task" if b.task else "mesh" if b.mesh else stage, "cbufs": [], "sbufs": [], "textures": [], "images": []}
    if stage == "vs" and getattr(b, "clip", 0):
        refl["clip"] = b.clip  # the clip distances it writes: a passthrough geometry stage after it passes them on
    if stage == "gs" and getattr(b, "gs_full", False):
        refl["emits"] = 1  # a geometry program that emits its own vertices (mtf-recomp), not a passthrough one
    if stage == "tes":  # what a geometry stage after it takes (mtf-recomp): 0 points, 1 lines, 2 triangles
        mode = getattr(b, "tess_mode", 0)
        refl["tess_out"] = 0 if (mode >> 8 & 3) == 0 else 1 if (mode & 3) == 0 else 2
    nb = 1
    for n in sorted(b.cbufs):
        head.append(f"layout(std140, binding = {nb}) uniform CB{n} {{ uvec4 d[4096]; }} cb{n};")
        refl["cbufs"].append({"binding": nb, "slot": n})
        nb += 1
        if n in b.cbufs_w:
            # The same bank as words for dynamic addresses (mem.cb_word), through a read-only storage view of its own
            # binding (flags 2: the back end binds the bank's range to it as a storage buffer) and bounded by that
            # range: a word past it reads 0, as the console's constant bank. Until 13/11/2026 this was a second uniform
            # block on the bank's own binding (`scalar`, uint w[16384]), the only aliased binding of the translation,
            # and NVIDIA (616-621, Turing to Blackwell) lost the device with "instruction pointer invalid" on draws of
            # vertex shaders whose only difference from a sound twin was one more such read (issue #22, programs
            # c74a0d4e / 852f48d6); the same pattern faulted in mkw-thwomp ("four reads of c9 at a computed index").
            head.append(f"layout(std430, binding = {nb}) readonly buffer CB{n}W {{ uint w[]; }} cb{n}w;")
            head.append(f"uint cb{n}w_at(uint i) {{ return i < uint(cb{n}w.w.length()) ? cb{n}w.w[i] : 0u; }}")
            refl["cbufs"].append({"binding": nb, "slot": n, "flags": 2})
            nb += 1
    for o in sorted(b.ssbos):
        head.append(f"layout(std430, binding = {nb}) buffer SB{o:x} {{ uint d[]; }} sb{o:x};")
        # flags 1: the shader stores into it. The replay copies such a range back to guest memory and keeps the CPU's
        # writes out of it until then; every buffer marked so hid the HUD's glyph records (01/11/2026).
        refl["sbufs"].append({"binding": nb, "slot": len(refl["sbufs"]), "cb_slot": 0, "cb_offset": o // 4,
                              "flags": 1 if o in b.ssbos_written else 0})  # fmt: skip
        nb += 1
    for (bank, idx), t in sorted(b.textures.items()):
        head.append(f"layout(binding = {nb}) uniform {t} t{bank}_{idx};")
        refl["textures"].append({"binding": nb, "type": sampler_type(t), "format": "Unknown", "cbuf_slot": bank,
                                 "handle": idx, "array": 1, "separate": False, "flags": 0})  # fmt: skip
        nb += 1
    for (bank, idx), t in sorted(b.images.items()):
        fmt = "r32ui, " if t.startswith("uimage") else ""
        head.append(f"layout({fmt}binding = {nb}) uniform {t} i{bank}_{idx};")
        # flags 4: the shader stores into it (mtf-recomp; was every image, as the buffers' flag 1 once was). The replay
        # takes such an image as written by the GPU and copies it back to guest memory. Mario Tennis Fever's text writes
        # each glyph on the CPU into a pitch-linear staging texture that a compute program only loads from to fill the
        # glyph cache: marked written, its stale image was copied back over the new glyphs and the text drew none.
        refl["images"].append({"binding": nb, "type": sampler_type(t), "format": "R32Uint" if fmt else "Unknown", "cbuf_slot": bank,
                               "handle": idx, "array": 1, "separate": False,
                               "flags": 4 if (bank, idx) in b.images_written else 0})  # fmt: skip
        nb += 1
    for bank, idx in sorted(b.txq_tex):
        n = {"sampler1D": 1, "sampler2D": 2, "sampler3D": 3, "samplerCube": 2, "sampler2DArray": 3,
             "samplerCubeArray": 3, "sampler1DArray": 2}.get(b.textures[(bank, idx)].replace("Shadow", ""), 2)  # fmt: skip
        sz = f"textureSize(t{bank}_{idx}, l)"
        v = sz if n == 3 else f"ivec3({sz}, 1)" if n == 2 else f"ivec3({sz}, 1, 1)"
        head.append(f"ivec3 txqsz_{bank}_{idx}(int l) {{ return {v}; }}")
    # Specialization constants of the fixed-address constant words (Builder.const); "spec" lists each k's [bank, byte].
    for (bank, byte), k in b.spec.items():
        head.append(f"layout(constant_id = {2 * k}) const bool SCU{k} = false;")
        head.append(f"layout(constant_id = {2 * k + 1}) const uint SCV{k} = 0u;")
    refl["spec"] = [[bank, byte] for (bank, byte), _ in sorted(b.spec.items(), key=lambda e: e[1])]
    b.reflection = refl
    return head


# Passthrough geometry programs (mtf-recomp; core.translate takes only those): the program's body, sm_main(), sets the
# per-primitive outputs, then main() passes each input vertex on unchanged with them and emits the primitive, as the
# console does after OUT.FINAL. The module is written for triangles and every attribute Location; the runtime adapts
# it to each pipeline (runtime/gfx/vk/pipe/vk_spirv_patch.c spirv_gs_adapt): the input topology (its execution modes,
# the length of the per-vertex input arrays and GS_NV), the Locations the vertex stage does not write (removed, as
# Vulkan requires every input to be written) and GS_CLIP, the clip distances the vertex stage writes ("clip" in its
# reflection). Distances past GS_CLIP are 1.0: inside. The point size goes on too: with the device's
# shaderTessellationAndGeometryPointSize, which the runtime requires for this stage, points need it. The ids are the runtime's GS_NV_SPEC_ID and GS_CLIP_SPEC_ID.
# A viewport mask (NV_viewport_array2, which only NVIDIA's Vulkan drivers have) sends the primitive to every viewport
# whose bit is set: GS_VIEWPORTS invocations, NVN's viewport count, each emitting it into its own viewport when its bit
# is set (the way emulators take it to other GPUs).
GS_NV_ID, GS_CLIP_ID, GS_ATTRS, GS_VIEWPORTS = 4000, 4001, 32, 16


def gs_head(b) -> list[str]:
    invocations = f", invocations = {GS_VIEWPORTS}" if "gs_viewport_mask" in b.gs_writes else ""
    return [
        f"layout(triangles{invocations}) in;",
        "layout(triangle_strip, max_vertices = 3) out;",
        f"layout(constant_id = {GS_NV_ID}) const int GS_NV = 3;",
        f"layout(constant_id = {GS_CLIP_ID}) const int GS_CLIP = 0;",
        "in gl_PerVertex { vec4 gl_Position; float gl_PointSize; float gl_ClipDistance[8]; } gl_in[];",
        "out gl_PerVertex { vec4 gl_Position; float gl_PointSize; float gl_ClipDistance[8]; };",
        *[f"layout(location = {a}) in vec4 in_attr{a}[];" for a in range(GS_ATTRS)],
        *[f"layout(location = {a}) out vec4 out_attr{a};" for a in range(GS_ATTRS)],
        "int gs_layer = 0, gs_viewport = 0, gs_viewport_mask = 0;",
    ]


# Tessellation and full geometry programs (mtf-recomp; mem.vtg_attr). The input gl_PerVertex block has the members of
# the passthrough geometry stage's (gs_head): Position, PointSize, ClipDistance[8] last, which the runtime fits to the
# stage before (vk_spirv_patch.c); the output block has Position and PointSize only, so a last stage before the
# rasterizer writes no clip distances it never set. Per-vertex user attributes at their Location, per-patch ones from
# Location 31 down (mem.patch_location).
# SET_TESSELLATION_PARAMETERS (NVIDIA clb197.h, MIT): domain 1:0 isoline/triangle/quad, spacing 5:4 integer/fractional
# odd/fractional even, output primitives 9:8 points/lines/triangles CW/triangles CCW. The TES's control section holds
# that word at +0x5c (0x202 for the quads of Mario Tennis Fever's court). Vulkan's cw with its default upper-left
# domain origin is the hardware's TRIANGLES_CW (Mesa NVK nvk_cmd_draw.c, MIT).
TESS_DOMAIN = {0: "isolines", 1: "triangles", 2: "quads"}
TESS_SPACING = {0: "equal_spacing", 1: "fractional_odd_spacing", 2: "fractional_even_spacing"}
GS_OUT_TOPOLOGY = {1: "points", 6: "line_strip", 7: "triangle_strip"}  # SPH word 3 bits 24-27 (Ryujinx, MIT)


def tes_layout(mode: int) -> str:
    domain, spacing, prims = TESS_DOMAIN.get(mode & 3), TESS_SPACING.get(mode >> 4 & 3), mode >> 8 & 3
    if domain is None or spacing is None:
        raise Unsupported(f"tes: tessellation parameters {mode:#x}")
    parts = [domain, spacing]
    if prims == 0:
        parts.append("point_mode")
    elif domain != "isolines" and prims in (2, 3):
        parts.append("cw" if prims == 2 else "ccw")
    return f"layout({', '.join(parts)}) in;"


def vtg_head(b) -> list[str]:
    stage, head = b.stage, []
    clash = sorted(set(b.in_attrs if stage == "tes" else b.out_attrs) & {31 - p for p in b.patch_attrs})
    if clash:
        raise Unsupported(f"{stage}: per-patch Locations {clash} taken by per-vertex attributes")
    if stage == "tcs":
        verts = b.sph.words[2] >> 24 if b.sph else 0
        if not 1 <= verts <= 32:
            raise Unsupported(f"tcs: {verts} output vertices")
        head.append(f"layout(vertices = {verts}) out;")
    elif stage == "tes":
        head.append(tes_layout(b.tess_mode))
    else:
        topo = GS_OUT_TOPOLOGY.get(b.sph.words[3] >> 24 & 0xF if b.sph else 0)
        verts = b.sph.words[4] & 0xFFF if b.sph else 0
        if topo is None or not 1 <= verts <= 1024:
            raise Unsupported(f"gs: output topology {b.sph.words[3] >> 24 & 0xF if b.sph else 0}, {verts} vertices")
        invocations = (b.sph.words[2] >> 24) if b.sph else 1
        inv = f", invocations = {invocations}" if invocations > 1 else ""
        head += [f"layout(triangles{inv}) in;", f"layout({topo}, max_vertices = {verts}) out;",
                 f"layout(constant_id = {GS_NV_ID}) const int GS_NV = 3;"]  # fmt: skip
    head.append("in gl_PerVertex { vec4 gl_Position; float gl_PointSize; float gl_ClipDistance[8]; } gl_in[];")
    head.append(f"out gl_PerVertex {{ vec4 gl_Position; float gl_PointSize; }}{' gl_out[]' if stage == 'tcs' else ''};")
    head += [f"layout(location = {a}) in vec4 in_attr{a}[];" for a in sorted(b.in_attrs)]
    arr = "[]" if stage == "tcs" else ""
    head += [f"layout(location = {a}) out vec4 out_attr{a}{arr};" for a in sorted(b.out_attrs)]
    if b.patch_attrs:
        if stage not in ("tcs", "tes"):
            raise Unsupported(f"{stage}: per-patch attributes")
        q = "patch out" if stage == "tcs" else "patch in"
        head += [f"layout(location = {31 - p}) {q} vec4 patch_attr{p};" for p in sorted(b.patch_attrs)]
    return head


def gs_viewport_relative(b) -> bool:
    """SPH byte 0x4f bit 0, the reserved byte after the output map's fixed-function textures (eden-nx2
    program_header.h names the byte OmapReserved; idea only): read here as NV_viewport_array2's viewport-relative
    layer, layer = layer + viewport index. The one program met with it (Mario Tennis Fever's shadow caster) sends each
    primitive to the cascades' viewports by a viewport mask, while the pass binds a 4-layer depth array with four
    viewports, one cascade each, and writes no layer: on the console each cascade lands in its own layer."""
    return bool(b.sph and len(b.sph.words) > 19 and b.sph.words[19] >> 24 & 1)


def gs_main(b) -> str:
    per_primitive, skip = [], []
    relative = gs_viewport_relative(b)
    viewport = None
    if "gs_viewport_mask" in b.gs_writes:  # the mask decides the viewport; the index is ignored with it
        skip.append("    if ((uint(gs_viewport_mask) >> uint(gl_InvocationID) & 1u) == 0u) return;")
        viewport = "gl_InvocationID"
    elif "gs_viewport" in b.gs_writes:
        viewport = "gs_viewport"
    if viewport:
        per_primitive.append(f"        gl_ViewportIndex = {viewport};")
    if relative and viewport:
        per_primitive.append(f"        gl_Layer = gs_layer + {viewport};")
    elif "gs_layer" in b.gs_writes:
        per_primitive.append("        gl_Layer = gs_layer;")
    return "\n".join([
        "void main() {",
        "    sm_main();",
        *skip,
        "    for (int v = 0; v < GS_NV; v++) {",
        "        gl_Position = gl_in[v].gl_Position;",
        "        gl_PointSize = gl_in[v].gl_PointSize;",   # the vertex stage always writes it (core.py)
        "        for (int c = 0; c < 8; c++) gl_ClipDistance[c] = c < GS_CLIP ? gl_in[v].gl_ClipDistance[c] : 1.0;",
        *[f"        out_attr{a} = in_attr{a}[v];" for a in range(GS_ATTRS)],
        *per_primitive,
        "        EmitVertex();",
        "    }",
        "    EndPrimitive();",
        "}",
    ])


# Task programs: 32 invocations a workgroup (a warp: the programs use lane masks and ballots), the payload as a uint
# array, the mesh count in shared memory; EmitMeshTasksEXT runs once, after every invocation has finished the program
# (on the console the last lane writes the count and exits).
TASK_MAIN = """void main() {
    if (gl_LocalInvocationIndex == 0u) task_count = 0u;
    barrier();
    sm_main();
    barrier();
    EmitMeshTasksEXT(task_count, 1u, 1u);
}
"""


# Mesh programs: 32 invocations, outputs kept in shared memory while the program runs (MV_WORDS words in the SKEW
# layout, index bytes, the primitive count), then emitted: 32 vertices with the position and generics 0-15, triangles.
# The outputs start at zero: shared memory keeps the previous workgroup's bytes on AMD, and an index or vertex the
# program leaves unwritten drew long triangles across the shadow map (Hookshot ae4fb30, RX 7700S; GPL: the idea only).
MESH_GENERICS = 16
MESH_ZERO = """    for (uint k = gl_LocalInvocationIndex; k < MV_WORDS; k += 32u) mv[k] = 0u;
    for (uint k = gl_LocalInvocationIndex; k < MESH_PRIMS * 3u; k += 32u) mib[k] = 0u;
"""
MESH_MAIN = (
    """void main() {
    if (gl_LocalInvocationIndex == 0u) mprims = 0u;
"""
    + MESH_ZERO
    + """    barrier();
    sm_main();
    barrier();
    uint np = min(mprims, MESH_PRIMS), v = gl_LocalInvocationIndex;
    SetMeshOutputsEXT(32u, np);
    gl_MeshVerticesEXT[v].gl_Position = uintBitsToFloat(uvec4(mv[v], mv[32u + v], mv[64u + v], mv[96u + v]));
"""
    + "".join(f"    out_attr{g}[v] = uintBitsToFloat(uvec4(mv[{(4 + 4 * g) * 32}u + v], mv[{(5 + 4 * g) * 32}u + v], "
              f"mv[{(6 + 4 * g) * 32}u + v], mv[{(7 + 4 * g) * 32}u + v]));\n" for g in range(MESH_GENERICS))
    + """    for (uint p = v; p < np; p += 32u) gl_PrimitiveTriangleIndicesEXT[p] = uvec3(mib[3u * p], mib[3u * p + 1u], mib[3u * p + 2u]);
}
"""
)


def mesh_head(head: list[str]) -> list[str]:
    out = [head[0], "#extension GL_EXT_mesh_shader : require", *head[1:]]
    out += ["layout(local_size_x = 32) in;", "layout(triangles, max_vertices = 32, max_primitives = 64) out;",
            "#define WG_INDEX gl_WorkGroupID.x",
            "const uint MESH_PRIMS = 64u;", f"const uint MV_WORDS = {(4 + 4 * MESH_GENERICS) * 32}u;",
            f"taskPayloadSharedEXT uint tp[{ThreadOps.TASK_WORDS}];", "shared uint mv[MV_WORDS];",
            "shared uint mib[MESH_PRIMS * 3u];", "shared uint mprims;"]  # fmt: skip
    out = [x for x in out if not x.startswith("layout(location") and "gl_ClipDistance" not in x]
    return out + [f"layout(location = {g}) out vec4 out_attr{g}[];" for g in range(MESH_GENERICS)]


def task_head(head: list[str]) -> list[str]:
    out = [head[0], "#extension GL_EXT_mesh_shader : require", *head[1:]]
    out += ["layout(local_size_x = 32) in;", f"taskPayloadSharedEXT uint tp[{ThreadOps.TASK_WORDS}];",
            "shared uint task_count;", "#define WG_INDEX gl_WorkGroupID.x"]  # fmt: skip
    return [x for x in out if not x.startswith("layout(location") and "gl_ClipDistance" not in x]


# Task/mesh as compute, for devices without VK_EXT_mesh_shader (the idea from AnyPS5
# #6528, no code): the same translated body, other wrappers. Buffers by address (push constants): trec the task records
# (TASK_REC words a workgroup: the payload, then task_count, at most MESH_PER_TASK: a ballot count in MKW's 7 task
# programs), mmap the mesh workgroups the tasks asked for, packed as task << 5 | index (runtime/shaders/mesh/mesh_compact.comp
# between the two passes, which also writes the indirect dispatch and draw), mvo the vertices (MESH_VWORDS words each:
# position and the MESH_GENERICS generics) and mto the triangles as absolute vertex indices, those past the mesh's
# count written degenerate. The draw is indexed, through MESH_CS_VS.
MESH_PER_TASK = 32
MESH_VWORDS = 4 + 4 * MESH_GENERICS
TASK_REC = 1024 + 1
# The three buffers by GPU address in push constants (bufferDeviceAddress, core in Vulkan 1.2): the programs' own set 0
# stays as it is, and the runtime adds only a push-constant range to these layouts.
CS_BUFFERS = [
    "#extension GL_EXT_buffer_reference : require",
    "#extension GL_EXT_shader_explicit_arithmetic_types_int64 : require",
    "layout(buffer_reference, std430, buffer_reference_align = 4) buffer U32s { uint d[]; };",
    "layout(push_constant) uniform MeshPass { U32s trec, mvo, mto, map; uint has_task; } mp;",
    "#define trec mp.trec",
    "#define mvo mp.mvo",
    "#define mto mp.mto",
    "#define mmap mp.map",
]

TASK_MAIN_CS = f"""void main() {{
    if (gl_LocalInvocationIndex == 0u) task_count = 0u;
    barrier();
    sm_main();
    barrier();
    uint base = gl_WorkGroupID.x * {TASK_REC}u;
    for (uint k = gl_LocalInvocationIndex; k < {TASK_REC - 1}u; k += 32u) trec.d[base + k] = tp[k];
    if (gl_LocalInvocationIndex == 0u) trec.d[base + {TASK_REC - 1}u] = min(task_count, {MESH_PER_TASK}u);
}}
"""

MESH_MAIN_CS = (
    f"""void main() {{
    // with a task: the packed workgroup's task and index (runtime/shaders/mesh/mesh_compact.comp), launched only as many
    // as the tasks asked for
    uint g = gl_WorkGroupID.x, t = HAS_TASK ? mmap.d[g] >> 5 : 0u, v = gl_LocalInvocationIndex;
    bool live = true;
    if (v == 0u) mprims = 0u;
{MESH_ZERO}    if (HAS_TASK) for (uint k = v; k < {TASK_REC - 1}u; k += 32u) tp[k] = trec.d[t * {TASK_REC}u + k];
    barrier();
    if (live) sm_main();
    barrier();
    uint np = live ? min(mprims, MESH_PRIMS) : 0u, vb = (g * 32u + v) * {MESH_VWORDS}u;
    for (uint k = 0u; k < {MESH_VWORDS}u; k++) mvo.d[vb + k] = mv[k * 32u + v];
    for (uint p = v; p < MESH_PRIMS; p += 32u)
        for (uint k = 0u; k < 3u; k++) mto.d[(g * MESH_PRIMS + p) * 3u + k] = g * 32u + (p < np ? mib[3u * p + k] : 0u);
}}
"""
)

# The vertex shader of every mesh-as-compute draw: the vertex the mesh workgroup wrote, read as MESH_VWORDS / 4
# attributes of one vertex buffer (the vertex buffer is mvo, stride MESH_VWORDS * 4), so the graphics layout needs no
# push constants. A prepared shader like the others, under the fixed key MESH_CS_VS_KEY (runtime gfx_shader.c).
MESH_CS_VS = "\n".join(
    ["#version 460"]
    + [f"layout(location = {a}) in vec4 v{a};" for a in range(MESH_VWORDS // 4)]
    + [f"layout(location = {g}) out vec4 out_attr{g};" for g in range(MESH_GENERICS)]
    + ["void main() {", "    gl_Position = v0;"]
    + [f"    out_attr{g} = v{g + 1};" for g in range(MESH_GENERICS)]
    + ["}", ""]
)
MESH_CS_VS_KEY = "6d6b772d6d6573682d63732d76732d31" * 2   # "mkw-mesh-cs-vs-1" twice, as hex: not a program key


def mesh_head_cs(head: list[str]) -> list[str]:
    """mesh_head as a compute shader: tp is shared memory filled from the task's record."""
    out = [*head, "layout(local_size_x = 32) in;", "const uint MESH_PRIMS = 64u;",
           f"const uint MV_WORDS = {(4 + 4 * MESH_GENERICS) * 32}u;",
           # the runtime knows whether a task program comes first (the pipeline's pair), the translator does not
           "#define HAS_TASK (mp.has_task != 0u)",
           "#define WG_INDEX (HAS_TASK ? mmap.d[gl_WorkGroupID.x] & 31u : gl_WorkGroupID.x)",
           f"shared uint tp[{ThreadOps.TASK_WORDS}];", "shared uint mv[MV_WORDS];", "shared uint mib[MESH_PRIMS * 3u];",
           "shared uint mprims;", *CS_BUFFERS]  # fmt: skip
    return [x for x in out if not x.startswith("layout(location") and "gl_ClipDistance" not in x]


def task_head_cs(head: list[str]) -> list[str]:
    out = [*head, "layout(local_size_x = 32) in;", f"shared uint tp[{ThreadOps.TASK_WORDS}];", "shared uint task_count;",
           "#define WG_INDEX gl_WorkGroupID.x", *CS_BUFFERS]  # fmt: skip
    return [x for x in out if not x.startswith("layout(location") and "gl_ClipDistance" not in x]

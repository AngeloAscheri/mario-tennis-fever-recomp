// Mario Tennis Fever's own SDK replacements (mtf-recomp): the calls nxboot (exefs/main) makes that Mario Kart World
// never did.
//
// nxboot's boot function (main+0x660) mounts the RomFS, registers the .nrr with nn::ro, unpacks the engine into a
// buffer with six threads and hands it to nn::ro::LoadModule; nnMain then calls the engine's one export, Abort()
// (docs/research.md, "The engine payload"). Here the engine is already mapped and linked at boot as the module
// "basic" (lifted from tools/unpack_engine.py's copy), so LoadModule checks that the buffer nxboot built is that same
// engine and runs its constructors, as ro does on the console.
#include <stdint.h>
#include <string.h>

#include "host.h"
#include "ov.h"
#include "version.h"

void rt_boot_ro_init(Cpu *c, const char *name);   // boot.c

static void ov_nothing(Cpu *c) { (void)c; }
static void ov_ok(Cpu *c) { ret_x(c, 0); }

// Result nn::ro::Initialize(): an IPC to ldr:ro on the console, so its caller blocks and the threads it has started
// run first. nxboot's six unpacking threads read their arguments from its stack, which it reuses right after
// (kern_settle in kernel.c says how); 50 ms is far more than their first steps take.
static void ov_ro_initialize(Cpu *c) {
    int pending = kern_settle(50000000);
    if (pending) rt_log("ov_mtf: nn::ro::Initialize: %d started threads had not run after 50 ms", pending);
    ret_x(c, 0);
}

static const RtLoaded *loaded(const char *name) {
    for (int i = 0; i < ldr_count(); i++)
        if (!strcmp(ldr_module(i)->name, name)) return ldr_module(i);
    rt_fatal("ov_mtf: module %s is not loaded", name);
}

// Result nn::ro::GetBufferSize(size_t *size, const void *image): the engine's .bss is part of the image the loader
// mapped, so ro needs no buffer.
static void ov_ro_buffer_size(Cpu *c) {
    ST64(arg_x(c, 0), 0);
    ret_x(c, 0);
}

// Result nn::ro::LoadModule(Module *module, const void *image, void *buffer, size_t size, int bind)
static void ov_ro_load_module(Cpu *c) {
    const char *name = rt_version()->ro_module;
    if (!name) rt_fatal("ov_mtf: nn::ro::LoadModule, but this game version names no ro module");
    const RtLoaded *m = loaded(name);
    const uint8_t *image = (const uint8_t *)(uintptr_t)arg_x(c, 1);
    // text and rodata are as the file has them (relocations only write the data segment, loader.c)
    if (memcmp(image, (const void *)(uintptr_t)m->base, m->data_off))
        rt_fatal("ov_mtf: the module nxboot built is not %s as tools/unpack_engine.py rebuilt it", name);
    rt_log("ov_mtf: nn::ro::LoadModule: nxboot's buffer is %s (%#llx bytes of code and rodata agree)", name,
           (unsigned long long)m->data_off);
    rt_boot_ro_init(c, name);
    ret_x(c, 0);
}

HOST_OVERRIDE("_ZN2nn2fs12SetAllocatorEPFPvmEPFvS1_mE", ov_nothing);
HOST_OVERRIDE("_ZN2nn2ro10InitializeEv", ov_ro_initialize);
HOST_OVERRIDE("_ZN2nn2ro18RegisterModuleInfoEPNS0_16RegistrationInfoEPKv", ov_ok);
HOST_OVERRIDE("_ZN2nn2ro13GetBufferSizeEPmPKv", ov_ro_buffer_size);
HOST_OVERRIDE("_ZN2nn2ro10LoadModuleEPNS0_6ModuleEPKvPvmi", ov_ro_load_module);

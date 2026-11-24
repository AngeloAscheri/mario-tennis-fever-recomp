// mtf-recomp: R_AARCH64_TLSDESC, the thread-local variables of a dynamically loaded module.
//
// Mario Tennis Fever's engine (basic, an NRO) has 10 TLSDESC relocations, all against its own TLS block (no symbol,
// addends 0 to 0x50: gRPC's thread-local contexts among them); Mario Kart World has none. A TLSDESC is a pair of GOT
// words: a resolver and its argument. The code calls `blr [desc]` with x0 = desc and adds the x0 it gets back to
// TPIDR_EL0, so the resolver returns (this thread's copy of the variable) - TPIDR_EL0 and keeps every other register.
//
// Here the argument is the variable's offset in the module's TLS block, and each guest thread gets its own block the
// first time it asks, zero-filled. That is the right initial value for a .tbss (the gRPC contexts are pointers that
// start null); a module with a .tdata template would need that template copied in, so a non-zero addend beyond the
// block is fatal rather than guessed. Keyed by TPIDR_EL0, which kernel.c gives every guest thread (its TLS area).
#include <stdint.h>
#include <string.h>

#include "host.h"
#include "platform/platform.h"

#define TLS_BLOCK 0x400    // bytes per thread: the engine's highest offset is 0x50 plus an 8-byte variable
#define TLS_THREADS 1024   // guest threads that may ask (the game creates a few dozen)

static PlatMutex lock;
static uint64_t arena;     // TLS_THREADS blocks, mem_runtime_alloc: guest-visible
static uint64_t owner[TLS_THREADS];   // the TPIDR_EL0 each block belongs to, 0 when free
static int used;

static uint64_t block_for(uint64_t tp) {
    plat_mutex_lock(&lock);
    if (!arena) {
        arena = mem_runtime_alloc((uint64_t)TLS_BLOCK * TLS_THREADS, "TLSDESC blocks");
        if (!arena) rt_fatal("tlsdesc: no memory for the thread-local blocks");
    }
    for (int i = 0; i < used; i++) {
        if (owner[i] == tp) {
            plat_mutex_unlock(&lock);
            return arena + (uint64_t)i * TLS_BLOCK;
        }
    }
    if (used == TLS_THREADS) rt_fatal("tlsdesc: more than %d threads use thread-local variables", TLS_THREADS);
    int i = used++;
    owner[i] = tp;
    uint64_t b = arena + (uint64_t)i * TLS_BLOCK;
    memset((void *)(uintptr_t)b, 0, TLS_BLOCK);
    plat_mutex_unlock(&lock);
    return b;
}

static void resolver(Cpu *c) {
    uint64_t off = LD64(c->x[0] + 8);
    if (off + 8 > TLS_BLOCK) rt_fatal("tlsdesc: offset %#llx is past the %#x-byte block", (unsigned long long)off, TLS_BLOCK);
    c->x[0] = block_for(c->tpidr) + off - c->tpidr;
}

// The resolver's guest address, for the loader to write into each descriptor's first word.
uint64_t ldr_tlsdesc_resolver(void) {
    static uint64_t addr;
    if (!addr) addr = hostfn_register("mtf:tlsdesc", resolver);
    return addr;
}

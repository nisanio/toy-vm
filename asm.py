asmbuf = [0] * 0xffff
asmptr = asmbuf + 0x3000
asmrun = 0

def _R(n):
    return (n & 7) | 0xa000

def NR(r):
    return r & 7

def DR(r):
    return NR(r) << 9

def SR(r):
    return NR(r) << 6

def IR(x):
    if (x >> 12) == 0xa:
        return NR(x)
    else:
        return (x & 0x1f) | 0x20

def A9(a):
    return a & 0x1ff

R0 = _R(0)
R1 = _R(1)
R2 = _R(2)
R3 = _R(3)
R4 = _R(4)
R5 = _R(5)
R6 = _R(6)
R7 = _R(7)

def _L(x):
    x
    return asmptr - asmbuf - 1

def PC():
    return asmptr - asmbuf

def DW(n):
    asmptr.append(n)
    return PC() - 1

def LL(label):
    return label - PC() - 1

def BR(addr):
    _L(asmptr.append(0x0e00 | A9(LL(addr))))


def BRN(addr):
    _L(asmptr.append(0x0800 | A9(LL(addr))))


def BRZ(addr):
    _L(asmptr.append(0x0400 | A9(LL(addr))))


def BRP(addr):
    _L(asmptr.append(0x0200 | A9(LL(addr))))


def BRNZ(addr):
    _L(asmptr.append(0x0c00 | A9(LL(addr))))


def BRNP(addr):
    _L(asmptr.append(0x0a00 | A9(LL(addr))))


def BRZP(addr):
    _L(asmptr.append(0x0600 | A9(LL(addr))))


def ADD(x, y, z):
    _L(asmptr.append(0x1000 | DR(x) | SR(y) | IR(z)))


def AND(x, y, z):
    _L(asmptr.append(0x5000 | DR(x) | SR(y) | IR(z)))


def NOT(x, y):
    _L(asmptr.append(0x9000 | DR(x) | SR(y) | 0x3f))


def LEA(x, addr):
    _L(asmptr.append(0xe000 | DR(x) | A9(LL(addr))))


def LD(x, addr):
    _L(asmptr.append(0x2000 | DR(x) | A9(LL(addr))))


def LDI(x, addr):
    _L(asmptr.append(0xa000 | DR(x) | A9(LL(addr))))


def ST(x, addr):
    _L(asmptr.append(0x3000 | DR(x) | A9(LL(addr))))


def STI(x, addr):
    _L(asmptr.append(0xb000 | DR(x) | A9(LL(addr))))


def LDR(x, y, z):
    _L(asmptr.append(0x6000 | DR(x) | SR(y) | (z & 0x3f)))


def STR(x, y, z):
    _L(asmptr.append(0x7000 | DR(x) | SR(y) | (z & 0x3f)))


def JMP(x):
    _L(asmptr.append(0xc000 | SR(x)))


def JSR(addr):
    _L(asmptr.append(0x4800 | A9(LL(addr))))


def RET():
    _L(asmptr.append(0xc000 | SR(R7)))


def TRAP(op):
    _L(asmptr.append(0xf000 | (op & 0xff)))


def GETC():
    _L(TRAP(0x20))


def PUTC():
    _L(TRAP(0x21))


def HALT():
    _L(TRAP(0x25))


def LC3ASM():
    global asmrun
    for asmrun in range(2):
        if asmrun and (asmptr = asmbuf + 0x3000):
            asmrun -= 1



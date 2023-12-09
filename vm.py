import sys
import select
import termios
import tty

R_R0 = 0
R_R1 = 1
R_R2 = 2
R_R3 = 3
R_R4 = 4
R_R5 = 5
R_R6 = 6
R_R7 = 7
R_PC = 8  # program counter
R_COND = 9
R_COUNT = 10

FL_POS = 1 << 0  # P
FL_ZRO = 1 << 1  # Z
FL_NEG = 1 << 2  # N

OP_BR = 0  # branch
OP_ADD = 1  # add
OP_LD = 2  # load
OP_ST = 3  # store
OP_JSR = 4  # jump register
OP_AND = 5  # bitwise and
OP_LDR = 6  # load register
OP_STR = 7  # store register
OP_RTI = 8  # unused
OP_NOT = 9  # bitwise not
OP_LDI = 10  # load indirect
OP_STI = 11  # store indirect
OP_JMP = 12  # jump
OP_RES = 13  # reserved (unused)
OP_LEA = 14  # load effective address
OP_TRAP = 15  # execute trap

MR_KBSR = 0xFE00  # keyboard status
MR_KBDR = 0xFE02  # keyboard data

TRAP_GETC = 0x20  # get character from keyboard, not echoed onto the terminal
TRAP_OUT = 0x21  # output a character
TRAP_PUTS = 0x22  # output a word string
TRAP_IN = 0x23  # get character from keyboard, echoed onto the terminal
TRAP_PUTSP = 0x24  # output a byte string
TRAP_HALT = 0x25  # halt the program

MEMORY_MAX = (1 << 16)
memory = [0] * MEMORY_MAX  # 65536 locations
reg = [0] * R_COUNT

original_tio = termios.tcgetattr(sys.stdin)


def disable_input_buffering():
    tty.setcbreak(sys.stdin.fileno())


def restore_input_buffering():
    termios.tcsetattr(sys.stdin, termios.TCSANOW, original_tio)


def check_key():
    return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])


def handle_interrupt(signal, frame):
    restore_input_buffering()
    sys.exit(-2)


def sign_extend(x, bit_count):
    if (x >> (bit_count - 1)) & 1:
        x |= (0xFFFF << bit_count)
    return x


def swap16(x):
    return (x << 8) | (x >> 8)


def update_flags(r):
    if reg[r] == 0:
        reg[R_COND] = FL_ZRO
    elif reg[r] >> 15:  # a 1 in the left-most bit indicates negative
        reg[R_COND] = FL_NEG
    else:
        reg[R_COND] = FL_POS


def read_image_file(file):
    # the origin tells us where in memory to place the image
    origin = int.from_bytes(file.read(2), "big")
    # we know the maximum file size so we only need one read
    max_read = MEMORY_MAX - origin
    p = memory[origin:]
    read = file.read(max_read * 2)
    for i in range(0, len(read), 2):
        p[i // 2] = int.from_bytes(read[i:i + 2], "big")


def read_image(image_path):
    try:
        with open(image_path, "rb") as file:
            read_image_file(file)
    except FileNotFoundError:
        return False
    return True


def mem_write(address, val):
    memory[address] = val


def mem_read(address):
    if address == MR_KBSR:
        if check_key():
            memory[MR_KBSR] = (1 << 15)
            memory[MR_KBDR] = ord(sys.stdin.read(1))
        else:
            memory[MR_KBSR] = 0
    return memory[address]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # show usage string
        print("lc3 [image-file1] ...")
        sys.exit(2)

    for j in range(1, len(sys.argv)):
        if not read_image(sys.argv[j]):
            print(f"failed to load image: {sys.argv[j]}")
            sys.exit(1)

    signal.signal(signal.SIGINT, handle_interrupt)
    disable_input_buffering()

    # since exactly one condition flag should be set at any given time, set the Z flag
    reg[R_COND] = FL_ZRO

    # set the PC to starting position
    # 0x3000 is the default
    PC_START = 0x3000
    reg[R_PC] = PC_START

    running = True
    while running:
        # FETCH
        instr = mem_read(reg[R_PC])
        reg[R_PC] += 1
        op = instr >> 12

        if op == OP_ADD:
            # destination register (DR)
            r0 = (instr >> 9) & 0x7
            # first operand (SR1)
            r1 = (instr >> 6) & 0x7
            # whether we are in immediate mode
            imm_flag = (instr >> 5) & 0x1
            if imm_flag:
                imm5 = sign_extend(instr & 0x1F, 5)
                reg[r0] = reg[r1] + imm5
            else:
                r2 = instr & 0x7
                reg[r0] = reg[r1] + reg[r2]
            update_flags(r0)

        elif op == OP_AND:
            r0 = (instr >> 9) & 0x7
            r1 = (instr >> 6) & 0x7
            imm_flag = (instr >> 5) & 0x1
            if imm_flag:
                imm5 = sign_extend(instr & 0x1F, 5)
                reg[r0] = reg[r1] & imm5
            else:
                r2 = instr & 0x7
                reg[r0] = reg[r1] & reg[r2]
            update_flags(r0)

        elif op == OP_NOT:
            r0 = (instr >> 9) & 0x7
            r1 = (instr >> 6) & 0x7
            reg[r0] = ~reg[r1]
            update_flags(r0)

        elif op == OP_BR:
            pc_offset = sign_extend(instr & 0x1FF, 9)
            cond_flag = (instr >> 9) & 0x7
            if cond_flag & reg[R_COND]:
                reg[R_PC] += pc_offset

        elif op == OP_JMP:
            # Also handles RET
            r1 = (instr >> 6) & 0x7
            reg[R_PC] = reg[r1]

        elif op == OP_JSR:
            long_flag = (instr >> 11) & 1
            reg[R_R7] = reg[R_PC]
            if long_flag:
                long_pc_offset = sign_extend(instr & 0x7FF, 11)
                reg[R_PC] += long_pc_offset  # JSR
            else:
                r1 = (instr >> 6) & 0x7
                reg[R_PC] = reg[r1]  # JSRR

        elif op == OP_LD:
            r0 = (instr >> 9) & 0x7
            pc_offset = sign_extend(instr & 0x1FF, 9)
            reg[r0] = mem_read(reg[R_PC] + pc_offset)
            update_flags(r0)

        elif op == OP_LDI:
            r0 = (instr >> 9) & 0x7
            pc_offset = sign_extend(instr & 0x1FF, 9)
            reg[r0] = mem_read(mem_read(reg[R_PC] + pc_offset))
            update_flags(r0)

        elif op == OP_LDR:
            r0 = (instr >> 9) & 0x7
            r1 = (instr >> 6) & 0x7
            offset = sign_extend(instr & 0x3F, 6)
            reg[r0] = mem_read(reg[r1] + offset)
            update_flags(r0)

        elif op == OP_LEA:
            r0 = (instr >> 9) & 0x7
            pc_offset = sign_extend(instr & 0x1FF, 9)
            reg[r0] = reg[R_PC] + pc_offset
            update_flags(r0)

        elif op == OP_ST:
            r0 = (instr >> 9) & 0x7
            pc_offset = sign_extend(instr & 0x1FF, 9)
            mem_write(reg[R_PC] + pc_offset, reg[r0])

        elif op == OP_STI:
            r0 = (instr >> 9) & 0x7
            pc_offset = sign_extend(instr & 0x1FF, 9)
            mem_write(mem_read(reg[R_PC] + pc_offset), reg[r0])

        elif op == OP_STR:
            r0 = (instr >> 9) & 0x7
            r1 = (instr >> 6) & 0x7
            offset = sign_extend(instr & 0x3F, 6)
            mem_write(reg[r1] + offset, reg[r0])

        elif op == OP_TRAP:
            reg[R_R7] = reg[R_PC]
            trap_vector = instr & 0xFF
            if trap_vector == TRAP_GETC:
                # read a single ASCII char
                reg[R_R0] = ord(sys.stdin.read(1))
                update_flags(R_R0)
            elif trap_vector == TRAP_OUT:
                sys.stdout.write(chr(reg[R_R0]))
                sys.stdout.flush()
            elif trap_vector == TRAP_PUTS:
                # one char per word
                c = memory[reg[R_R0]]
                while c != 0:
                    sys.stdout.write(chr(c))
                    c = memory[c]
                sys.stdout.flush()
            elif trap_vector == TRAP_IN:
                sys.stdout.write("Enter a character: ")
                sys.stdout.flush()
                reg[R_R0] = ord(sys.stdin.read(1))
                sys.stdout.write("\n")
                sys.stdout.flush()
                update_flags(R_R0)
            elif trap_vector == TRAP_PUTSP:
                # one char per byte (two bytes per word)
                c = memory[reg[R_R0]]
                while c != 0:
                    sys.stdout.write(chr(c & 0xFF))
                    c >>= 8
                    if c != 0:
                        sys.stdout.write(chr(c & 0xFF))
                        c >>= 8
                sys.stdout.flush()
            elif trap_vector == TRAP_HALT:
                print("HALT")
                sys.stdout.flush()
                running = False

        else:
            sys.exit(1)

    restore_input_buffering()



import logging
import re
import itertools
import struct
import ast


def _parse_number(val):
    if val.startswith("0x"):  # parse hex
        val = int(val, 16)
    elif val.endswith("b"):  # parse binary
        if '_' in val:
            val = val.replace('_', '')
        val = int(val.replace('b', ''), 2)
    else:  # decimal
        val = int("".join(itertools.takewhile(str.isdigit, val)))
    return val


def _strip_line(line):
    # clean comments and whitespaces
    if ";" in line:
        line = line[:line.index(";")]
    return line.strip()


def _tokenize_line(line):
    line = _strip_line(line)

    if '+' in line or '*' in line:
        a = 5

    tokens = re.split("\W+", line)

    # command is always the first word
    cmd = tokens[0]
    # params are separated by ','
    params = [p.strip() for p in line.replace(cmd, '').split(',')]

    return cmd, params


def _eval_statement(stmt, labels):
    class ResolveLabel(ast.NodeTransformer):
        def __init__(self, labels):
            self.labels = labels

        def visit_Name(self, node):
            return ast.copy_location(
                ast.Num(n=self.labels.get(node.id, node.id),
                        ctx=node.ctx),
                node)

    node = ast.parse(stmt.strip(), mode="eval")
    # resolve labels to their numerical value
    node = ResolveLabel(labels).visit(node)
    try:
        val = ast.literal_eval(node)
    except Exception as e:
        a = 5

    return val


def _determine_opsize(dst, src):
    return 4


def _parse_descriptor_defines(lines, labels=None):
    segbytes = bytearray()
    for l in lines:
        segbytes += _parse_descr_bytes(*_tokenize_line(l), labels)
    return segbytes


def _parse_descr_bytes(cmd, vals, labels={}):
    count = _get_define_bytecount(cmd)

    res = bytearray()
    for v in vals:
        try:
            val = _parse_number(v)
        except ValueError:
            if v in labels:
                val = labels[v]
            else:
                logging.error("Couldn't parse descriptor byte: '{} {}'"
                              .format(cmd, ','.join(vals)))
                val = 0
        b = [(val & (0xFF << (8 * n))) >> 8 * n for n in range(count)]
        res += bytearray(b)
    return res


def _parse_segment_descriptor(segbytes):
    try:
        if len(segbytes) < 8:
            # add dummy bytes so parsing with the other bytes still works
            segbytes += bytearray((8 - len(segbytes)) * b'\xff')

        seglimit, baseaddr1, baseaddr2, flags, misc, baseaddr3 = (
            struct.unpack('HHBBBB', segbytes))
    except struct.error as e:
        logging.error("Couldn't unpack segment descriptor, because: {}"
                      .format(e))
        seglimit, baseaddr1, baseaddr2, flags, misc, baseaddr3 = (
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00)

    seglimit_h = misc & 0x0f
    seglimit += (seglimit_h << 16)
    baseaddr = baseaddr1 + (baseaddr2 << 16) + (baseaddr3 << 24)

    return {
        "seglimit": seglimit,
        "base_addr": baseaddr,
        "type": flags & 0x0f,  # segment type
        "s": bool(flags & 0x10),  # descr type 0 = system; 1 = code or data
        "dpl": (flags & 0x60) >> 5,  # descriptor privilege level
        "p": bool(flags & 0x80),  # segment present
        "avl": bool(misc & 0x10),  # available for use by system software
        "l": bool(misc & 0x20),  # 64-bit code segment (IA-32e mode only)
        "db": bool(misc & 0x40),  # def op size (0 = 16-bit, 1 = 32 bit seg)
        "g": bool(misc & 0x80)  # granularity
    }


def _parse_interrupt_descriptor(intbytes):
    try:
        if len(intbytes) < 8:
            # add dummy bytes so parsing with the other bytes still works
            intbytes += bytearray((8 - len(intbytes)) * b'\xff')

        ofs1, seg_sel, dummy, flags, ofs2 = struct.unpack("HHBBH", intbytes)
    except struct.error as e:
        logging.error("Couldn't unpack segment descriptor, because: {}"
                      .format(e))
        ofs1, seg_sel, dummy, flags, ofs2 = 0x00, 0x00, 0x00, 0x00, 0x00

    type_id = flags & 0x07
    if type_id == 0b110:
        int_type = "interrupt_gate"
    elif type_id == 0b101:
        int_type = "task_gate"
    elif type_id == 0b111:
        int_type = "trap_gate"
    else:
        int_type = "invalid"

    return {
        "offset": ofs1 + (ofs2 << 16),
        "segment": seg_sel,  # segment
        "dummy": dummy,  # only 0s
        "int_type": int_type,  # fix for all interrupt gates
        "d": (flags & 0x08) >> 3,  # size of gate, 1 = 32 bits, 0 = 16 bits
        "dpl": (flags & 0x60) >> 4,  # descriptor privilege level
        "p": bool(flags * 0x80)  # present flag
    }


def _get_define_bytecount(cmd):
    cmd = cmd.lower()
    if cmd == "dw":
        return 2
    elif cmd == "db":
        return 1
    elif cmd == "dd":
        return 4
    else:
        logging.warning("Invalid command when determining bytecount")
        return 0


class Registers:
    def __init__(self):
        self._regs = {
            "eax": 0,
            "ebx": 0,
            "ecx": 0,
            "edx": 0,
            "esi": 0,
            "edi": 0,
            "ebp": 0,
            "esp": 0,

            # segments
            "cs": 0,
            "ds": 0,
            "es": 0,
            "fs": 0,
            "gs": 0,
            "ss": 0,

            # special
            "cr0": 0,
            "cr1": 0,
            "cr2": 0,
            "cr3": 0,
            "eflags": 0
        }

    def __getitem__(self, reg):
        reg, mask = self._get_reg_key(reg)
        val = self._regs[reg]

        return val & mask if mask else val

    def __setitem__(self, reg, value):
        reg, mask = self._get_reg_key(reg)

        if mask:
            self._regs[reg] = value & mask
        else:
            self._regs[reg] = value

    def __iter__(self):
        return self._regs.__iter__()

    @staticmethod
    def _is_segment(name):
        name = name.lower()
        if len(name) == 2 and name[1] == 's':
            return name[0] in "cdefgs"

        return False

    def _get_reg_key(self, name):
        """
        Get the proper key of the given register name
        :param name: name of the register which should be looked up
        :return: 2-tuple of full name of the register and mask to access the
        wanted byte(s), if the registername indicates a restriction
        """
        name = name.lower()
        if len(name) == 3 and name in self._regs:
            return name, None
        elif len(name) == 2:
            if self._is_segment(name):
                return name, None
            elif name[-1] in ['x', 'h', 'l'] and name[0] in 'abcd':
                mask = (0xffff if name[-1] == 'x' else
                        0xff00 if name[-1] == 'h' else 0x00ff)
                return ''.join(['e', name[0], 'x']), mask
            else:
                return name in ["si", 'di', 'bp', 'sp'], None


class AsmInterpreter:
    def __init__(self, code, labels=None):
        self.lines = code
        # self.regs = self._init_registers()
        self.regs = Registers()
        self.labels = labels if labels is not None else self.extract_labels()

    def extract_labels(self):
        labels = {}
        for nr, l in enumerate([_strip_line(l) for l in self.lines]):
            label = None
            val = -1

            if ':' in l:
                label = l.replace(':', '')
                val = nr
            elif 'equ' in l:
                # extract label
                idx = l.index(' equ ')
                label = l[:idx]

                # parse definition
                idx += 5
                stmt = l[idx:].replace('$', str(nr))
                val = _eval_statement(stmt, labels)
            elif 'db' in l:
                idx = l.index('db')
                if idx > 1:
                    label = l[:idx].strip()
                    val = nr

            if label:
                labels[label] = val

        return labels

    def interpret(self, lines=None):
        if lines is None:
            lines = self.lines

        for l in lines:
            cmd, params = _tokenize_line(l)
            fn = self._get_function(cmd)
            if fn:
                res = fn(params)
            else:
                logging.warning("Didn't handle line '{}'".format(l))
            pass

        return self.regs

    def parse_segment_descriptors(self, lines=None):
        if lines is None:
            lines = self.lines

        segments = {}
        seg_bytes = []
        seg_name = None
        for l in lines:
            l = _strip_line(l)
            if "equ $-gdt" in l:
                if seg_name:
                    segments[seg_name] = _parse_descriptor_defines(
                        seg_bytes, self.labels)
                seg_name = l[:l.index(" ")]
                seg_bytes.clear()
            elif "gdt_end:" in l:
                segments[seg_name] = _parse_descriptor_defines(
                    seg_bytes, self.labels)
            elif seg_name:
                seg_bytes.append(l)

        for k, v in segments.items():
            segments[k] = _parse_segment_descriptor(v)

        return segments

    def parse_descriptors(self, is_seg_descriptor=True):
        lines = []
        is_define_cmd = False
        for l in self.lines:
            if "idt:" in l:
                is_define_cmd = True
            elif "idt_end:" in l:
                break
            elif is_define_cmd:
                lines.append(l)

        descrbytes = _parse_descriptor_defines(lines, self.labels)
        bytes_per_entry = 8
        entries = [descrbytes[x:x + bytes_per_entry] for x in
                   range(0, len(descrbytes), bytes_per_entry)]

        parser = (_parse_segment_descriptor if is_seg_descriptor
                  else _parse_interrupt_descriptor)

        return [parser(bs) for bs in entries]

    def get_register(self, reg_name):
        return self.regs[reg_name]

    def _read_register(self, reg):
        pass

    def _write_register(self, reg, value):
        pass

    def _is_register(self, name):
        name = name.lower()
        if len(name) == 3 and name in self.regs:
            return True
        elif len(name) == 2:
            if name[1] in ['x', 'h', 'l'] and name[0] in ['a', 'b', 'c', 'd']:
                return True
            else:
                return name in ["si", 'di', 'bp', 'sp']

        return False

    def _resolve_value(self, src):
        try:
            if any((c in '+-*/') for c in src):
                try:
                    val = eval(src)
                except Exception as e:
                    logging.warning("couldn't evaluate expression '{}'"
                                    .format(src))
                    val = _parse_number(src)
            else:
                val = _parse_number(src)
        except ValueError:  # src is no value
            if self._is_register(src):
                val = self.regs[src]
            elif src in self.labels:
                val = self.labels[src]
            else:
                logging.warning("Invalid source value: {}".format(src))
                val = 0
                # val = self.regs[src] if self._is_register(src) else src
        return val

    def _get_function(self, cmd):
        cmd = cmd.lower()
        if cmd == "mov":
            return self._move
        elif cmd == "or":
            return self._or
        # elif cmd in ["jmp", "jz", "jnz", "jne" "jgt"]:
        #     pass
        # elif cmd == "int":
        #     pass
        # elif cmd == "call":
        #     pass
        # elif cmd == ["retn", "iret"]:
        #     pass
        # elif cmd == "cmp":
        #     pass
        # elif cmd == "dec":
        #     pass
        # elif cmd == "inc":
        #     pass
        # elif cmd == "push":
        #     pass
        # elif cmd == "pop":
        #     pass
        # elif cmd == "shl":
        #     pass
        else:
            logging.warning("Command '{}' not recognized!".format(cmd))

    def _move(self, params):
        if len(params) > 2:
            opsize, dst, src = params[0], params[1], params[2]
        else:
            dst, src = params[0], params[1]
            opsize = _determine_opsize(dst, src)

        # TODO handle [] operations as well as different opsizes
        val = self._resolve_value(src)

        if len(params) <= 3:
            self.regs[dst] = val
        else:
            logging.warning("--- strange move cmd: mov {}"
                            .format(' '.join(params)))

    def _or(self, params):
        dst, src = params[0], params[1]
        val = self._resolve_value(src)

        self.regs[dst] |= val

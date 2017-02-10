from unittest import TestCase

from asm_interpreter import AsmInterpreter, Registers, _determine_opsize, \
    _tokenize_line, _parse_number


class TestAsmInterpreter(TestCase):
    def test_interpret(self):
        lines = [
            "mov eax, cr0",
            "or al, 0x01	; setPE ( protection enabled) bit in CR0",
            "mov cr0, eax"
        ]
        asm = AsmInterpreter(lines)

        regs = asm.interpret()

        self.assertEqual(regs["cr0"] & 0x01, 1)

    def test__move(self):
        asm = AsmInterpreter([])

        _, params = _tokenize_line("mov eax, 0x03")
        asm._move(params)
        self.assertEqual(asm.get_register("eax"), 3)
        # asm = AsmInterpreter([])
        self.assertEqual(asm.get_register("ecx"), 0)
        _, params = _tokenize_line("mov ecx, eax")
        asm._move(params)
        self.assertEqual(asm.get_register("eax"), 3)
        self.assertEqual(asm.get_register("ecx"), 3)

    def test__or(self):
        asm = AsmInterpreter([])

        self.assertEqual(asm.get_register("eax"), 0)
        _, params = _tokenize_line("or eax, 0x08")
        asm._or(params)
        self.assertEqual(asm.get_register("eax"), 8)

        _, params = _tokenize_line("or eax, 0x01")
        asm._or(params)
        self.assertEqual(asm.get_register("eax"), 9)

    def test__is_register(self):
        asm = AsmInterpreter([])

        self.assertTrue(asm._is_register("eax"))
        self.assertTrue(asm._is_register("EAX"))
        self.assertTrue(asm._is_register("bx"))
        self.assertTrue(asm._is_register("ch"))
        self.assertTrue(asm._is_register("dl"))
        self.assertTrue(asm._is_register("esi"))
        self.assertTrue(asm._is_register("si"))
        self.assertTrue(asm._is_register("edi"))
        self.assertTrue(asm._is_register("di"))
        self.assertTrue(asm._is_register("ebp"))
        self.assertTrue(asm._is_register("bp"))
        self.assertTrue(asm._is_register("esp"))
        self.assertTrue(asm._is_register("sp"))

        self.assertFalse(asm._is_register("cs"))
        self.assertFalse(asm._is_register("DS"))
        self.assertFalse(asm._is_register("ES"))
        self.assertFalse(asm._is_register("xy"))

    def test__is_segment(self):
        asm = AsmInterpreter([])
        reg = Registers()

        self.assertTrue(reg._is_segment("cs"))
        self.assertTrue(reg._is_segment("DS"))
        self.assertTrue(reg._is_segment("es"))
        self.assertTrue(reg._is_segment("fs"))
        self.assertTrue(reg._is_segment("gs"))
        self.assertTrue(reg._is_segment("Ss"))
        self.assertTrue(reg._is_segment("fs"))

        self.assertFalse(reg._is_segment("a"))
        self.assertFalse(reg._is_segment("csd"))
        self.assertFalse(reg._is_segment("eax"))
        self.assertFalse(reg._is_segment("hs"))

    def test__parse_descriptors(self):
        labels = {
            "code": 150,
            "data": 160,
            "video": 170,
            "interrupthandler1": 180,
            "interrupthandler2": 190
        }

        lines = [
            "idtr:",
            "dw idt_end - idt - 1;",
            "dd idt;",
            "idt:",
            "dd 0, 0;",
            "; int 1: interrupt gate",
            "dw interrupthandler1",
            "dw code",
            "db 0x00				; 000 + reserved bits",
            "db 10001110b			; 0)= Lvl 0, 0, D( 1)= 32 bit, 110",
            "dw 0x00 ; int 2",
            "dw interrupthandler2",
            "dw code",
            "db 0x00					; 000 + reserved bits",
            "db 10001110b	; P(1), DPL ( 0)= Lvl 0, 0, D( 1)= 32 bit, 110",
            "dw 0x80",
            "idt_end:"
        ]
        asm = AsmInterpreter(lines, labels)
        descrs = asm.parse_descriptors(is_seg_descriptor=False)

        self.assertEqual(len(descrs), 3)

        empty_descr = {
            "offset": 0,
            "segment": 0,
            "dummy": 0,
            "int_type": "invalid",
            "d": 0,
            "dpl": 0,
            "p": 0
        }
        self.assertDictEqual(descrs[0], empty_descr)
        int_descr = {
            "offset": labels["interrupthandler1"],
            "segment": labels["code"],
            "dummy": 0,
            "int_type": "interrupt_gate",
            "d": 1,
            "dpl": 0,
            "p": True
        }

        self.assertDictEqual(descrs[1], int_descr)

        # 0x80 << 16 is for using page via 3rd PDE
        int_descr["offset"] = (labels["interrupthandler2"] + (0x80 << 16))
        self.assertDictEqual(descrs[2], int_descr)

    def test__determine_opsize(self):
        self.fail()

    def test__parse_number(self):
        val = _parse_number('0x03')
        self.assertEqual(val, 3)

        val = _parse_number('1337')
        self.assertEqual(val, 1337)

        val = _parse_number('1010101b')
        self.assertEqual(val, 85)

        with self.assertRaises(ValueError):
             val = _parse_number('eax')
        with self.assertRaises(ValueError):
             val = _parse_number('x03')
        with self.assertRaises(ValueError):
             val = _parse_number('\x03')


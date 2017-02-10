from unittest import TestCase
import exc3_protected as exc


class TestExerciseHandler(TestCase):
    def test__extract_tasks(self):
        self.fail()

    def test__extract_task(self):
        self.fail()

    def test__parse_seg_descriptor(self):
        lines = ["dw 0000110000000000b",
                 "dw 0xB00",
                 "db 10110b",
                 "db 10111011b",
                 "dw 0x0501"]
        res = exc._parse_descriptor_defines(lines)

        self.assertEquals(res, bytearray(b'\x00\x0C\x00\x0B\x16\xBB\x01\x05'))

    def test__parse_descr_bytes(self):
        cmd = "dw"
        val = "0000110000000000b"

        res = exc._parse_descr_bytes(cmd, val)
        self.assertEqual(res, bytearray(b'\x00\x0C'))

        val = "110000000000b"
        res = exc._parse_descr_bytes(cmd, val)
        self.assertEqual(res, bytearray(b'\x00\x0C'))

        val = "10000b"
        res = exc._parse_descr_bytes(cmd, val)
        self.assertEqual(res, bytearray(b'\x10\x00'))

        val = "0xB800"
        res = exc._parse_descr_bytes(cmd, val)
        self.assertEqual(res, bytearray(b'\x00\xB8'))

        # single byte results
        cmd = "db"
        val = "10000b"
        res = exc._parse_descr_bytes(cmd, val)
        self.assertEqual(res, bytearray(b'\x10'))

        val = "0000110000000000b"
        res = exc._parse_descr_bytes(cmd, val)
        self.assertEqual(res, bytearray(b'\x00'))

        val = "10110011b"
        res = exc._parse_descr_bytes(cmd, val)
        self.assertEqual(res, bytearray(b'\xB3'))

        # 4 byte results
        cmd = "dd"
        val = "10000b"
        res = exc._parse_descr_bytes(cmd, val)
        self.assertEqual(res, bytearray(b'\x10\x00\x00\x00'))

    def test__parse_segment_descriptor(self):
        segbytes = bytearray(b'\xff\x0b\x00\x00\x00\x9e\xc0\x00')
        res = exc._parse_segment_descriptor(segbytes)

        ref_dict = {
            "seglimit": 0xbff,
            "base_addr": 0,
            "type": 14,
            "s": True,
            "dpl": 0,
            "p": True,
            "avl": False,
            "l": False,
            "db": True,
            "g": True
        }

        self.assertDictEqual(res, ref_dict)

    def test__get_bytecount(self):
        self.fail()

    def test__eval_code_seg(self):
        # correct segment
        segbytes = bytearray(b'\xff\x0b\x00\x00\x00\x9e\xc0\x00')
        pts, penalties = exc._eval_code_seg(segbytes)
        self.assertEqual(pts, 0)
        self.assertListEqual(penalties, [])

        # malconfigured segment
        # lines = [
        #     "dw 0x7FFF",
        #     "dw 0x8000",
        #     "db 0x0B",
        #     "db 10110011b",
        #     "db 01000000b",
        #     "db 0x00"
        # ]
        # segbytes = exc._parse_descriptor_defines(lines)

        segbytes = bytearray(b'\xff\x7f\x00\x80\x0b\xb3\x40\x00')
        pts, penalties = exc._eval_code_seg(segbytes)
        self.assertLess(pts, 0)
        self.assertGreater(len(penalties), 4)

    def test__eval_data_seg(self):
        self.fail()

    def test__eval_video_seg(self):
        lines = [
            "dw 8000D",
            "dw 0x8000",
            "db 0x0B",
            "db 0x92",
            "db 0xD0",
            "db 0x00"
        ]
        segbytes = exc._parse_descriptor_defines(lines)
        res = exc._eval_video_seg(segbytes)

    def test__parse_int_descriptor(self):
        self.fail()

    def test_grade_submission(self):
        self.fail()

    def test__grade_task(self):
        self.fail()

    def test__grade_task1(self):
        self.fail()

    def test__grade_task2(self):
        self.fail()

    def test__grade_task3(self):
        self.fail()

    def test__grade_task4(self):
        self.fail()

    def test__grade_task5(self):
        self.fail()

    def test__grade_task7(self):
        self.fail()

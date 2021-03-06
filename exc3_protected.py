import os
import logging
import shutil
import functools
# from functools import partial

from asm_interpreter import AsmInterpreter, _parse_number, _tokenize_line

makefile_src = os.path.join("..", "data", "Makefile_3")
write_src = os.path.join("..", "data", "write_3.c")


def _eval_segment(seg, criteria, deduct):
    explanations = {
        "seglimit": "Falsches Segmentlimit: {}",
        "base_addr": "Falsche Basisadresse: {}",
        "type": "Falscher Segment Typ (type): {}",
        "s": "Falscher Descriptor Typ (s): {}",
        "dpl": "Falsches Privileg Level (dpl): {}",
        "p": "Segment muss praesent sein (p)",
        "avl": "Segment steht nicht fuer das System zur Verfuegung",
        "l": "Es handelt sich nicht um ein 64 Bit Segment (l)",
        "db": "Operation Size muss 32 Bit sein (db)",
        "g": "Granularität Bit muss gesetzt sein (g)"
    }

    for k, v in seg.items():
        if not criteria[k](v):
            deduct(1, explanations[k].format(v))


def _eval_code_seg(seg, deduct_fn):
    # deduced_pts = 0
    # penalties = []

    criteria = {
        "seglimit": lambda x: 3071 <= x <= 3072,
        "base_addr": lambda x: x == 0,
        "type": lambda x: x in [10, 11, 14, 15],
        "s": lambda x: x,
        "dpl": lambda x: x <= 1,
        "p": lambda x: x,
        "avl": lambda x: not x,
        "l": lambda x: not x,
        "db": lambda x: x,
        "g": lambda x: x
    }

    _eval_segment(seg, criteria, deduct_fn)

    # if not (3071 <= seg["seglimit"] <= 3072):
    #     deduced_pts += 1
    #     penalties.append("Falsches Segmentlimit: {}".format(seg["seglimit"]))
    # if seg["base_addr"] != 0:
    #     deduced_pts += 1
    #     penalties.append("Falsche Basisadresse: {}".format(seg["base_addr"]))
    # if seg["type"] not in [10, 11, 14, 15]:
    #     deduced_pts += 1
    #     penalties.append("Falscher Segment Typ (type): {}".format(seg["type"]))
    # if not seg["s"]:
    #     deduced_pts += 1
    #     penalties.append("Falscher Descriptor Typ (s): {}".format(seg["s"]))
    # if seg["dpl"] > 1:
    #     deduced_pts += 1
    #     penalties.append("Falsches Privileg Level (dpl): " + str(seg["dpl"]))
    # if not seg["p"]:
    #     deduced_pts += 1
    #     penalties.append("Segment muss praesent sein (p)")
    # if seg["avl"]:
    #     deduced_pts += 1
    #     penalties.append("Segment steht nicht fuer das System zur Verfuegung")
    # if seg["l"]:
    #     deduced_pts += 1
    #     penalties.append("Es handelt sich nicht um ein 64 Bit Segment (l)")
    # if not seg["db"]:
    #     deduced_pts += 1
    #     penalties.append("Operation Size muss 32 Bit sein (db)")
    # if not seg["g"]:
    #     deduced_pts += 1
    #     penalties.append("Granularität Bit muss gesetzt sein (g)")

    # return deduced_pts, penalties


def _eval_data_seg(seg, deduct_fn):
    deduced_pts = 0
    penalties = []

    if not (3071 <= seg["seglimit"] <= 3072):
        deduced_pts += 1
        penalties.append("Falsches Segmentlimit: {}".format(seg["seglimit"]))
    if seg["base_addr"] != 0:
        deduced_pts += 1
        penalties.append("Falsche Basisadresse: {}".format(seg["base_addr"]))
    if seg["type"] not in [2, 3]:
        deduced_pts += 1
        penalties.append("Falscher Segment Typ (type): {}".format(seg["type"]))
    if not seg["s"]:
        deduced_pts += 1
        penalties.append("Falscher Descriptor Typ (s): {}".format(seg["s"]))
    if seg["dpl"] > 1:
        deduced_pts += 1
        penalties.append("Falsches Privileg Level (dpl): " + str(seg["dpl"]))
    if not seg["p"]:
        deduced_pts += 1
        penalties.append("Segment muss praesent sein (p)")
    if seg["avl"]:
        deduced_pts += 1
        penalties.append("Segment steht nicht fuer das System zur Verfuegung")
    if seg["l"]:
        deduced_pts += 1
        penalties.append("Es handelt sich nicht um ein 64 Bit Segment (l)")
    if not seg["db"]:
        deduced_pts += 1
        penalties.append("Operation Size muss 32 Bit sein (db)")
    if not seg["g"]:
        deduced_pts += 1
        penalties.append("Granularität Bit muss gesetzt sein (g)")

    return deduced_pts, penalties


def _eval_video_seg(seg, deduct_fn):
    deduced_pts = 0
    penalties = []

    if not (0x7FFF <= seg["seglimit"] <= 0x8000):
        deduced_pts += 1
        penalties.append("Falsches Segmentlimit: {}".format(seg["seglimit"]))
    if seg["base_addr"] != 0xB8000:
        deduced_pts += 1
        penalties.append("Falsche Basisadresse: {}".format(seg["base_addr"]))
    if seg["type"] not in [2, 3]:
        deduced_pts += 1
        penalties.append("Falscher Segment Typ (type): {}".format(seg["type"]))
    if not seg["s"]:
        deduced_pts += 1
        penalties.append("Falscher Descriptor Typ (s): {}".format(seg["s"]))
    if seg["dpl"] > 1:
        deduced_pts += 1
        penalties.append("Falsches Privileg Level (dpl): " + str(seg["dpl"]))
    if not seg["p"]:
        deduced_pts += 1
        penalties.append("Segment muss praesent sein (p)")
    if seg["avl"]:
        deduced_pts += 1
        penalties.append("Segment steht nicht fuer das System zur Verfuegung")
    if seg["l"]:
        deduced_pts += 1
        penalties.append("Es handelt sich nicht um ein 64 Bit Segment (l)")
    if not seg["db"]:
        deduced_pts += 1
        penalties.append("Operation Size muss 32 Bit sein (db)")
    if seg["g"]:
        deduced_pts += 1
        penalties.append("Granularität Bit darf nicht gesetzt sein (g)")

    return deduced_pts, penalties


def _eval_int_descriptor(ref_descr, descr, tag="int"):
    deduced_pts = 0
    penalties = []

    if not (ref_descr == descr):
        for k, v1, v2 in zip(ref_descr.keys(), ref_descr.values(),
                             descr.values()):
            if not (v1 == v2):
                deduced_pts += 2
                penalties.append("[{}] {} falsch, es sollte {} statt {} sein"
                                 .format(tag, k, v1, v2))

    return deduced_pts, penalties


def _eval_int_call(lines, int_no):
    deduced_pts = 0
    penalties = []
    try:
        int_corr = True
        l = next(iter([l for l in lines if l.startswith("int ")]), '')
        cmd, params = _tokenize_line(l)

        if len(params) != 1:
            int_corr = False
            penalties.append("Interrupt 2 falsch aufgerufen")
        else:
            try:
                val = _parse_number(params[0])

                if val != int_no:
                    int_corr = False
                    penalties.append("Interrupt 2 wurde mit falschem "
                                     "Wert aufgerufen! {}".format(val))

            except ValueError:
                int_corr = False
                penalties.append("Interrupt 2 wurde mit ungueltigem Wert "
                                 "aufgerufen! {}".format(params[0]))

    except StopIteration:
        int_corr = False
        penalties.append("Interrupt 2 wurde nicht aufgerufen")

    if not int_corr:
        deduced_pts = 2

    return deduced_pts, penalties


class ExerciseHandler:
    _max_score = 60

    def __init__(self, wd):
        code = self._read_sourcecode(wd)
        self.tasks = self._extract_tasks(code)
        self.asm = AsmInterpreter(code)
        self.labels = {}
        self.score = self._max_score
        self.penalties = {}

    @staticmethod
    def get_exercise_name():
        return "Ue3"

    @classmethod
    def get_max_score(cls):
        return cls._max_score

    @staticmethod
    def normalize_files(wd):
        files = os.listdir(wd)

        # add Makefile for easier processing
        if "makefile" not in [f.lower() for f in files]:
            shutil.copyfile(makefile_src, os.path.join(wd, 'Makefile'))

        if "write.c" not in files:
            shutil.copyfile(write_src, os.path.join(wd, 'write.c'))

        # rename to protected.asm
        os.chdir(wd)
        if "protected.asm" not in files:
            for f in [f for f in files if f.endswith(".asm")]:
                os.replace(f, "protected.asm")
                break
        os.chdir("..")

    @staticmethod
    def _read_sourcecode(wd):
        with open(os.path.join(wd, "protected.asm"), encoding='latin-1') as f:
            lines = f.readlines()
        return lines

    def _extract_tasks(self, lines):
        return {
            1: self._extract_task(lines, 1),
            2: self._extract_task(lines, 2),
            3: self._extract_task(lines, 3),
            4: self._extract_task(lines, 4),
            5: self._extract_task(lines, 5),
            7: self._extract_task(lines, 7)
        }

    @staticmethod
    def _extract_task(code, task_nr):
        lines = []
        read_lines = False
        for l in code:
            if "<AUFGABE{}>".format(task_nr) in l:
                read_lines = True
            elif "</AUFGABE{}>".format(task_nr) in l:
                break
            elif read_lines:
                # another task started
                if "<AUFGABE".format(task_nr) in l:
                    break

                l = l.strip()
                if l and not l.startswith(";"):
                    lines.append(l)

        return lines

    def _deduct_points(self, task, score, pts, explanation):
        if task not in self.penalties:
            self.penalties[task] = []

        score -= pts
        if score < 0:
            score = 0
        self.penalties[task].append("[-{}] {}".format(pts, explanation))

    def grade_submission(self):
        for k, lines in self.tasks.items():
            self._grade_task(k, lines)

        return self.score, self.penalties

    def _grade_task(self, nr, lines):
        deduct_fn = functools.partial(self._deduct_points, nr)
        if nr == 1:
            return self._grade_task1(deduct_fn, lines)
        elif nr == 2:
            return self._grade_task2(deduct_fn, lines)
        elif nr == 3:
            return self._grade_task3(deduct_fn, lines)
        elif nr == 4:
            return self._grade_task4(deduct_fn, lines)
        elif nr == 5:
            return self._grade_task5(deduct_fn, lines)
        elif nr == 7:
            return self._grade_task7(deduct_fn, lines)
        else:
            return 0, ["Invalid task"]

    def _grade_task1(self, deduct_fn, lines):
        max_score = 15
        deduct_fn = functools.partial(deduct_fn, max_score)

        # asm = AsmInterpreter(lines)
        segments = self.asm.parse_segment_descriptors(lines)

        # penalties = []

        _eval_code_seg(segments["code"], deduct_fn)
        # max_score -= pts
        # penalties += pens

        _eval_data_seg(segments["data"], deduct_fn)
        # max_score -= pts
        # penalties += pens

        _eval_video_seg(segments["video"], deduct_fn)
        # max_score -= pts
        # penalties += pens

        if max_score < 0:
            logging.warning("capped negative score, because it would be {}"
                            .format(max_score))
            max_score = 0

        # return max_score, penalties

    def _grade_task2(self, deduct_fn, lines):
        max_score = 5
        asm = AsmInterpreter(lines)
        res = asm.interpret()

        if res["cr0"] & 0x01 == 0:
            return 0, ["PE Bit has to be enabled in CR0"]
        else:
            return max_score, []

    def _grade_task3(self, deduct_fn, lines):
        max_score = 10

        labels = {
            "code": 150,
            "data": 160,
            "video": 170
        }

        asm = AsmInterpreter(lines, labels)
        res = asm.interpret()

        penalties = []
        if not (asm.regs["ds"] == labels["data"]):
            max_score -= 2
            penalties.append("-2 Daten Segment falsch gesetzt")
        if not (asm.regs["ss"] == labels["data"]):
            max_score -= 2
            penalties.append("-2 Stack Segment falsch gesetzt")
        if not (asm.regs["es"] == labels["video"]):
            max_score -= 2
            penalties.append("-2 Extra Segment falsch gesetzt")
        if not (asm.regs["esp"] == 0xBFFFFF):
            max_score -= 4
            penalties.append("-4 Stack Pointer falsch gesetzt")
        if not (asm.regs["fs"] == 0):
            penalties.append("FS falsch gesetzt")
        if not (asm.regs["gs"] == 0):
            penalties.append("GS falsch gesetzt")

        return max_score, penalties

    def _grade_task4(self, deduct_fn, lines):
        max_score = 20

        labels = {
            "code": 150,
            "data": 160,
            "video": 170,
            "interrupthandler1": 180,
            "interrupthandler2": 190
        }
        # asm = AsmInterpreter(lines, labels)
        descrs = self.asm.parse_descriptors(lines, is_seg_descriptor=False)

        penalties = []
        if len(descrs) < 3:
            max_score -= 2
            penalties.append("Es muessen (mind) 3 Interrupts definiert sein")

        # check first interrupt
        int_descr = {
            "offset": labels["interrupthandler1"],
            "segment": labels["code"],
            "dummy": 0,
            "type": "interrupt_gate",
            "d": 1,
            "dpl": 0,
            "p": True
        }

        pts, pens = _eval_int_descriptor(int_descr, descrs[1], "int1")
        max_score -= pts
        penalties += pens

        # check interrupt for task 7
        int_descr["offset"] = (labels["interrupthandler2"] + (0x80 << 16))
        pts, pens = _eval_int_descriptor(int_descr, descrs[2], "int2")
        max_score -= pts
        penalties += pens

        if max_score < 0:
            logging.warning("capped negative score, because it would be {}"
                            .format(max_score))
            max_score = 0

        return max_score, penalties

    def _grade_task5(self, deduct_fn, lines):
        max_score = 5
        penalties = []

        found_ldtr = False
        for l in lines:
            if "lidt [idtr]" in l:
                found_ldtr = True
                break

        if not found_ldtr:
            max_score -= 3
            penalties.append("Interrupt Descriptor Table muss geladen werden")

        pts, pens = _eval_int_call(lines, 1)
        max_score -= pts
        penalties += pens

        return max_score, penalties

    def _grade_task7(self, deduct_fn, lines):
        max_score = 5
        penalties = []

        found_call = False
        for l in lines:
            if "call startpaging" in l:
                found_call = True
                break

        if not found_call:
            max_score -= 3
            penalties.append("Paging muss aktiviert werden")

        pts, pens = _eval_int_call(lines, 2)
        max_score -= pts
        penalties += pens

        return max_score, penalties


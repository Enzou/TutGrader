import os
import logging
import shutil
from zipfile import is_zipfile, ZipFile

from exc3_protected import ExerciseHandler
output_dir = "out"
report_name_template = "{}_grades.txt"


def extract_name(folder_name):
    # drop the generated suffix
    return "_".join(folder_name.split("_")[:-4])


def rename_submission_folders(wd):
    for d in os.listdir('.'):
        os.replace(d, extract_name(d))


def extract_submission(wd):
    files = os.listdir(wd)
    if len(files) > 1:
        logging.warning("{} contains more than 1 submission: {}"
                        .format(wd, ', '.join(files)))

    path = os.path.join(wd, files[0])

    # extract and delete submission
    if is_zipfile(path):
        try:
            with ZipFile(path) as sub:
                sub.extractall(wd)
            os.remove(path)
        except Exception:
            logging.warning("couldn't unzip " + str(path))

    # rename task folders
    files = os.listdir(wd)

    # probably intermediary folder
    src_dir = os.path.join(wd, files[0])
    if len(files) == 1 and os.path.isdir(src_dir):
        # move content from intermediary folder up
        for f in os.listdir(src_dir):
            shutil.move(os.path.join(src_dir, f), wd)
        os.rmdir(src_dir)


def handle_submissions(subs_src):
    prev_dir = os.getcwd()
    wd = output_dir
    if os.path.exists(wd):
        shutil.rmtree(wd)
    os.makedirs(wd)

    # unpack zip of all submissions
    with ZipFile(subs_src) as subs:
        subs.extractall(wd)

    # work in the output directory
    os.chdir(os.path.join(os.getcwd(), wd))

    rename_submission_folders(wd)

    # unpack zip of each submission
    # and grade submission
    grades = {}

    for d in os.listdir():
        extract_submission(d)

        ExerciseHandler.normalize_files(d)
        logging.info("-- Grading {} ".format(d))
        if "Lehrbaum" in d:
            a = 5
            logging.warning("~~~~~ skipping {}".format(d))
            continue
        grader = ExerciseHandler(d)
        grades[d] = grader.grade_submission()

    # restore previous working directory
    os.chdir(prev_dir)

    return grades


def print_report(grades, dst_file):
    with open(dst_file, mode='w', encoding='utf-8') as rep:
        for student in sorted(grades.keys()):
            grade = grades[student]
            rep.write("{} [{}/{}]:\n".format(
                student, grade[0], ExerciseHandler.get_max_score()))

            for task_nr, pens in grade[1].items():
                if len(pens) == 0:
                    continue

                rep.write('\tAufgabe {}:\n'.format(task_nr))
                for p in pens:
                    rep.write('\t\t{}\n'.format(p))
                rep.write('\n')

            rep.write('\n')


def main():
    submissions = "data/BSY1UE3.zip"
    grades = handle_submissions(submissions)
    rep_name = report_name_template.format(ExerciseHandler.get_exercise_name())
    print_report(grades, os.path.join(output_dir, rep_name))


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main()

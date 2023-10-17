"""For use by
test_py_holmes.TestWhenOriginalFileInDeeperFolder.test_file_creation_in_correct_folder_for_original_file_in_deeper_folder
"""


def create_dummy_file():
    with open("dummy_file.txt", "w", encoding="utf-8") as file:
        file.write("This is a dummy file created by dummy_file_creator.py")

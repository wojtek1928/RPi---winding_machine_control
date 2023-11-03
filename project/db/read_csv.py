import os
import csv
import glob
import time
from shutil import move


class Row:
    """
    Converts data from csv file to format used in the rest of program
    """

    def __init__(
            self,
            order_num: str,
            order_position: str,
            quantity: str,
            diameter: str,
            length: str,
            customer_name: str
    ):
        if len(order_position.strip()) > 0:
            self.order_id = f"{order_num.strip()}/{order_position.strip()}"
        else:
            self.order_id = f"{order_num.strip()}"
        self.quantity = int(quantity.strip())
        self.diameter = float(diameter.strip().replace(",", '.'))
        self.length = int(float(length.strip().replace(",", "."))*1000)
        self.customer_name = customer_name.strip()

    def __str__(self):
        return f"ORDER_ID: {self.order_id:{22}} QUANTITY: {self.quantity:{5}} DIAMETER: {self.diameter:{5}} LENGTH:{self.length:{8}} CUSTOMER_NAME: {self.customer_name}"


class CSVReader:
    def __init__(self) -> None:
        self.path_to_temp_dir = "/home/admin/Dokumenty/project/windows_SHARED/TEMP/"
        self.path_to_archive_dir = "/home/admin/Dokumenty/project/windows_SHARED/ARCHIVE/"
        self.orders_data = []

    def read_orders(self) -> list[Row]:
        """
        Read orders
        --
        1. Read all `.csv` files from `self.path_to_temp_dir `
        2. Create `Row` object for each readed row nad add them to list
        3. Return list of `Row` objects
        """
        # Read all `.csv` files from `self.path_to_temp_dir `
        self.files = glob.glob(f"{self.path_to_temp_dir}*.csv")

        for file in self.files:
            # Open each founded .csv file
            with open(file, 'r') as f:
                # Create `Row` object for each readed row nad add them to list
                for row in csv.reader(f, delimiter=';'):
                    row_to_save = Row(*row)
                    self.orders_data.append(row_to_save)

        # Return list of `Row` objects
        return self.orders_data

    def archive_read_files(self):
        """
        Archive read files
        ---
        Move files to `self.path_to_archive_dir` with new name (time postfix)
        """
        for file in self.files:
            # Get the current time in milliseconds
            current_time = int(time.time() * 1000)
            # Split the file's name and extension
            file_name, file_extension = os.path.splitext(
                file[len(self.path_to_temp_dir):])
            # Create a new name with the timestamp postfix
            new_name = f"{file_name}_{current_time}{file_extension}"
            # Construct the full path to the new location
            new_path = os.path.join(self.path_to_archive_dir, new_name)
            # Move the file to the new location with the new name
            move(file, new_path)

    def check_for_files_to_read(self):
        if glob.glob(f"{self.path_to_temp_dir}*.csv"):
            return True
        else:
            return False


if __name__ == "__main__":
    reader = CSVReader()
    if reader.check_for_files_to_read():
        print(reader.read_orders()[0].customer_name)
        reader.archive_read_files()
    else:
        print("TEMP dir is empty")

import sqlite3
import time
from loguru import logger

from db.read_csv import CSVReader, Row


class OrdersDB:
    def __init__(self) -> None:

        self.db_path = "project/windows_SHARED/DB/winding_machine.db"
        self.connection = sqlite3.connect(self.db_path)

    def get_all_rows(self):
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "SELECT order_id, status, quantity, length, diameter, customer_name, production_time, done_date FROM orders;")
            # Fetch all rows as a list of dictionaries
            columns = [column[0] for column in cursor.description]
            result = [dict(zip(columns, row)) for row in cursor.fetchall()]
            cursor.close()
            return result

        except sqlite3.Error as e:
            raise e

    def insert_row(self, data: list[Row] = None):
        """
        Insert rows into the database.
        --
        If there is a record with the same `order_id` as the row to insert, then this record is updated.
        """
        try:
            cursor = self.connection.cursor()
            for row_data in data:
                sql = """
                    INSERT INTO orders (
                        order_id,
                        customer_name,
                        quantity,
                        length,
                        diameter
                    ) VALUES (?, ?, ?, ?, ?);
                """
                data_input = (
                    row_data.order_id,
                    row_data.customer_name,
                    row_data.quantity,
                    row_data.length,
                    row_data.diameter
                )

                try:
                    cursor.execute(sql, data_input)
                except sqlite3.IntegrityError as e:
                    if e.__str__() == "UNIQUE constraint failed: orders.order_id":
                        # If the same order_id is in db then update the recored
                        sql_update = """
                        UPDATE orders
                        SET
                            customer_name=?,
                            quantity=?,
                            length=?,
                            diameter=?,
                            status='TODO',
                            done_date=null,
                            production_time=null
                        WHERE order_id=?
                        """
                        data_update_input = (
                            row_data.customer_name,
                            row_data.quantity,
                            row_data.length,
                            row_data.diameter,
                            row_data.order_id
                        )
                        cursor.execute(sql_update, data_update_input)

            cursor.close()
            self.connection.commit()  # Commit at the end
        except sqlite3.Error as e:
            raise e

    def read_csv_and_update_db(self):
        reader = CSVReader()
        time.sleep(2)
        if reader.check_for_files_to_read():
            data = reader.read_orders()
            self.insert_row(data)
            reader.archive_read_files()
            logger.success("New records inserted to database")
        else:
            logger.info("No .csv files were found")

    def set_done_status(self, order_id, production_time, done_date):
        try:
            sql = ''' 
            UPDATE orders
            SET
                status=?,
                production_time=?,
                done_date=? 
            WHERE order_id=?
            '''
            data_input = (
                'DONE',
                production_time,
                done_date,
                order_id
            )
            cursor = self.connection.cursor()
            cursor.execute(sql, data_input)
            self.connection.commit()
        except sqlite3.Error as e:
            raise e

class OrdersDBWorker()

if __name__ == "__main__":
    db = OrdersDB()
    db.read_csv_and_update_db()
    print(db.get_all_rows())

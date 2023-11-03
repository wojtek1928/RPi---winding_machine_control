import sqlite3
import time
from enum import Enum, auto
from loguru import logger
from PyQt5.QtCore import QRunnable, pyqtSignal, QThreadPool, QObject

from db.read_csv import CSVReader, Row


class OrdersDBActions(Enum):
    get_all_rows = auto()
    insert_row = auto()
    read_csv_and_update_db = auto()
    set_done_status = auto()
    set_interrupted_status = auto()


class OrdersDB:
    __is_executed = False

    def __init__(self) -> None:

        self.db_path = "project/windows_SHARED/DB/winding_machine.db"
        self.connection = sqlite3.connect(self.db_path)
        # Define actions object
        self.actions_handler = {
            OrdersDBActions.get_all_rows: self.get_all_rows,
            OrdersDBActions.insert_row: self.insert_row,
            OrdersDBActions.read_csv_and_update_db: self.read_csv_and_update_db,
            OrdersDBActions.set_done_status: self.set_done_status,
            OrdersDBActions.set_interrupted_status: self.set_interrupted_status
        }

    def execute(self, action_name: OrdersDBActions, *args, **kwargs):
        """
        Execute actions in a separate thread available in the `OrdersDBActions` class.
        Parametres:
        --
        - `name of action` - goes first
        - `*args` - optional or required depends on the function's execution.

        IMPORTANT
        --
        The order of parameters is important; the name of the action always goes first.
        """
        if not OrdersDB.__is_executed:
            logger.info(f"Exceuting: {action_name.name} ...")
            OrdersDB.__is_executed = True
            action = self.actions_handler[action_name]
            result = action(*args, **kwargs)
            OrdersDB.__is_executed = False
            return result

    def get_all_rows(self):
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "SELECT order_id, status, quantity, length, diameter, customer_name, production_time, done_date FROM orders ORDER BY status;")
            # Fetch all rows as a list of dictionaries
            columns = [column[0] for column in cursor.description]
            result = [dict(zip(columns, row)) for row in cursor.fetchall()]
            cursor.close()
            if not result:
                result = []
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
        if reader.check_for_files_to_read():
            data = reader.read_orders()
            self.insert_row(data)
            reader.archive_read_files()
            logger.success("New records inserted to database")
        else:
            logger.info("No .csv files were found")

        return self.get_all_rows()

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
            return self.get_all_rows()

        except sqlite3.Error as e:
            raise e

    def set_interrupted_status(self, order_id, production_time, done_date):
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
                'INTERRUPTED',
                production_time,
                done_date,
                order_id
            )
            cursor = self.connection.cursor()
            cursor.execute(sql, data_input)
            self.connection.commit()
            return self.get_all_rows()

        except sqlite3.Error as e:
            raise e


class Signals(QObject):
    started = pyqtSignal()
    done = pyqtSignal(list)
    error = pyqtSignal(str, str)


class OrdersDBWorker(QRunnable):
    def __init__(self, action_name: OrdersDBActions, *args, **kwargs):
        super().__init__()
        self.signals = Signals()

        self.action_name = action_name
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            self.db = OrdersDB()
            if self.action_name == OrdersDBActions.insert_row:
                self.db.execute(
                self.action_name, *self.args, **self.kwargs)
            else:
                result = self.db.execute(
                    self.action_name, *self.args, **self.kwargs)
                self.signals.done.emit(result)

        except Exception:
            logger.error("Failed to load data from winding_machine.db:orders")
            self.signals.error.emit(
                "Błąd bazy danych", "Skontaktuj się z administratorem sieci.\n Nie udane dodanie/pobranie danych.")


if __name__ == "__main__":
    db = OrdersDB()
    print(db.check_order_id_availability('280899/11/2023/1/9'))

    def after(result):
        print("xdxd")
        print("xd",result[0])

    # Thread definition
    pool = QThreadPool.globalInstance()
    worker = OrdersDBWorker(OrdersDBActions.get_all_rows, '280899/11/2023/1/9')
    # Done signal handling
    worker.signals.done.connect(after)
    # Error signal handling
    # worker.signals.error.connect(after)
    # Set action on thread start
    worker.signals.started.connect(worker.run)
    # Start thread
    pool.start(worker)

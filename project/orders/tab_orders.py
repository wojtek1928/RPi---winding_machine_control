import os
from enum import Enum, auto
from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow, QWidget, QTreeView, QPushButton
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QColor, QFont
from PyQt5.QtCore import QModelIndex
from loguru import logger
from regex import match

from machine_control import MachineControl
from encoder import Encoder
from buzzer import Buzzer
from LOGS.error_handling import ErrorDialog
from winding_in_progres import WindingInProgressDialog
from db.db import OrdersDB


class OrderStatus(str, Enum):
    DONE = "DONE"
    INTERRUPTED = "INTERRUPTED"
    TODO = "TODO"


class TreeItem(QStandardItem):
    def __init__(
            self,
            txt: str,
            color: QColor = QColor(127, 127, 127),
            font_size: int = 20,
            set_bold: bool = False,
            set_enabled: bool = False
    ):
        super().__init__()

        fnt = QFont("Open Sans", font_size)
        fnt.setBold(set_bold)

        self.setEditable(False)
        if color:
            self.setForeground(color)
        self.setFont(fnt)
        self.setText(txt)
        self.setSelectable(False)
        self.setEnabled(set_enabled)

    def onExpansion(self):
        print("Expanded")


class OrdersTab(QWidget):
    def __init__(
        self,
        parent_class: QMainWindow,
        ui_templates_dir: str,
        machine_control: MachineControl,
        encoder: Encoder,
        buzzer: Buzzer
    ):
        super().__init__()
        # try:
        self.machine_control = machine_control
        self.encoder = encoder
        self.buzzer = buzzer
        self.parent_class = parent_class
        self.ui_templates_dir = ui_templates_dir

        uic.loadUi(os.path.join(
            ui_templates_dir, "orders_tab.ui"), self)
        # Add tab to main window
        parent_class.tabWidget.addTab(self, "Zlecenia")

        # Flag for reading orders
        self.only_done: bool = False

        # self.orders = [
        #     {
        #         "order_id": "123456/12/1234/1/1",
        #         "quantity": 4,
        #         "length": 5000,
        #         "diameter": 2,
        #         "customer_name": "Jan Kowalski",
        #         # Wykonane  | Do wykonania | "Przerwane"
        #         "status": OrderStatus.DONE
        #         # production_date: "30.01.2023"
        #         # created_at: Timestap()
        #     },
        #     {
        #         "order_id": "123456/11/1234/1/2",
        #         "quantity": 2,
        #         "length": 1500,
        #         "diameter": 3.2,
        #         "customer_name": "Bogdan Nowak",
        #         "status": OrderStatus.INTERRUPTED
        #     }
        #     , {
        #         "order_id": "190902/10/2021/1/7",
        #         "quantity": 2,
        #         "length": 2002,
        #         "diameter": 1.9,
        #         "customer_name": "Oliwia Oleksy",
        #         "status": OrderStatus.TODO
        #     }
        # ]
        self.db = OrdersDB()
        self.orders = self.db.get_all_rows()
         
        # Define `pushButton_run` and handle clicked event
        self.pushButton_run: QPushButton
        self.pushButton_run.clicked.connect(self.runProccess)

        # Define `pushButton_toggleOrders` and handle clicked event
        self.pushButton_toggleOrders: QPushButton
        self.pushButton_toggleOrders.clicked.connect(self.toggleOrders)
        self.pushButton_toggleOrders.setStyleSheet("color: black;")

        # Define `pushButton_refresh` and handle clicked event
        self.pushButton_refresh: QPushButton
        self.pushButton_refresh.clicked.connect(self.refreshOrders)
        self.pushButton_refresh.setStyleSheet("color: black;")

        # Define `treeView` and fill it with data
        self.treeView: QTreeView
        self.treeModel = QStandardItemModel()
        # Assign model to `treeView`
        self.treeView.setModel(self.treeModel)

        # Define columns
        self.treeModel.setHorizontalHeaderLabels(['label', 'value'])
        # Define `rootNode`
        self.rootNode = self.treeModel.invisibleRootItem()

        # Handle item expansion event
        self.treeView.expanded.connect(self.onItemExpansion)
        # Handle item collapse event
        self.treeView.collapsed.connect(self.onItemCollapse)
        # Handle item selection event
        self.treeView.selectionModel().currentRowChanged.connect(self.onSelection)
        self.show_orders()

        # except Exception as e:
        #     print("Module OrdersTab initialization failed.", e, sep='\n')

    def show_orders(self):
        for order in self.orders:
            if self.only_done and order["status"] != OrderStatus.DONE:
                continue
            elif not self.only_done and order["status"] == OrderStatus.DONE:
                continue
            else:
                color = None
                status_label = ""
                if order["status"] == OrderStatus.INTERRUPTED:
                    color = QColor('#aa0000')
                    status_label = "Przerwane"
                elif order["status"] == OrderStatus.DONE:
                    color = QColor('#00aa00')
                    status_label = "Wykonane"
                elif order["status"] == OrderStatus.TODO:
                    color = QColor('#ffaa00')
                    status_label = "Do wykonania"

                # Assign order_id and status
                order_item = TreeItem(
                    order['order_id'],
                    set_bold=True,
                    font_size=24,
                    color=color,
                    set_enabled=True
                )
                status = TreeItem(
                    status_label,
                    color=color
                )
                # Assign customer_name (index = [0,1])
                customer_name_label = TreeItem("Nazwa klienta:")
                customer_name = TreeItem(order['customer_name'], set_bold=True)
                order_item.appendRow([customer_name_label, customer_name])
                # Assign quantity (index = [0,2])
                quantity_label = TreeItem("Ilość sztuk:")
                quantity = TreeItem(f"{order['quantity']}", set_bold=True)
                order_item.appendRow([quantity_label, quantity])
                # Assign length
                length_label = TreeItem("Długość [mm]:")
                length = TreeItem(f"{order['length']}", set_bold=True)
                order_item.appendRow([length_label, length])
                # Assign diameter
                diameter_label = TreeItem("Średnica [mm]:")
                diameter = TreeItem(f"{order['diameter']}", set_bold=True)
                order_item.appendRow([diameter_label, diameter])

                self.rootNode.appendRow([order_item, status])

    def onItemExpansion(self, index: QModelIndex):
        """
        Checks if expanded row is selected
        """
        item = self.treeModel.itemFromIndex(index)
        item.setSelectable(True)
        selectedIndexes = self.treeView.selectedIndexes()
        if selectedIndexes and self.treeView.selectedIndexes()[0] == index:
            self.pushButton_run.setEnabled(True)

    def onItemCollapse(self, index: QModelIndex):
        """
        Checks if collapsed row is selected, if is then disable `run_pushButton`
        """
        item = self.treeModel.itemFromIndex(index)
        item.setSelectable(False)
        selectedIndexes = self.treeView.selectedIndexes()
        if not selectedIndexes or self.treeView.selectedIndexes()[0] == index:
            self.pushButton_run.setDisabled(True)

    def onSelection(self, selected: QModelIndex):
        """
        Checks if selected row is expanded, if so, then enable `run_pushButton`, if not, disable
        """
        if self.treeView.isExpanded(selected):
            self.pushButton_run.setEnabled(True)
        else:
            self.pushButton_run.setDisabled(True)

    def toggleOrders(self):
        """
        Toggle between `done` or `todo` and `interrupted` orders
        """
        self.only_done = not self.only_done
        self.treeModel.removeRows(0, self.treeModel.rowCount())
        if self.only_done:
            self.pushButton_toggleOrders.setText("Pokaż do wykonania")
        else:
            self.pushButton_toggleOrders.setText("Pokaż wykonane")
        self.show_orders()

    def refreshOrders(self):
        self.pushButton_refresh.setText("xd")
        try:
             # Thread definition
            pool = QtCore.QThreadPool.globalInstance()
            worker = MachineWorker(self.__machine_control, action)
            # Error signal handling
            worker.signals.error_signal.connect(self.alert)
            # Set action on thread start
            worker.signals.started.connect(worker.run)
            # Start thread
            pool.start(worker)
            # Read new orders and add it to db
            self.db.read_csv_and_update_db()
            # Get all rows from db
            self.orders = self.db.get_all_rows()
            # Clean treeView
            self.treeModel.removeRows(0, self.treeModel.rowCount())
            # Show records
            self.show_orders()
            logger.info("Orders was refershed")
            self.pushButton_refresh.setEnabled(True)
        except Exception as e: 
            logger.error("Failed to load data from winding_machine.db:orders")
            self.alert("Błąd pobierania danych z bazy danych", "Skontaktuj się z administratorem sieci.")
        finally:
            pass

    # Alert handlingfunction
    def alert(self, err_title, err_desc):
        ErrorDialog(self.parent_class, err_title, err_desc, self.buzzer)

    def check_input(self):
        try:
            if self.treeView.selectedIndexes():
                selectedOrder = self.treeView.selectedIndexes()[0]
                # Read `customer_name`
                customer_name = selectedOrder.child(0, 1).data()
                # Read and valid `length`
                length = int(selectedOrder.child(2, 1).data())
                if length <= int(os.getenv('START_LENGHT')):
                    return False
                # Read and valid `quantity`
                quantity = int(selectedOrder.child(1, 1).data())
                if quantity <= 0:
                    return False
                # Read and valid `diameter`
                diameter = float(selectedOrder.child(3, 1).data())
                if diameter <= 0:
                    return False
                # Read and valid `order_id`
                order_id = str(selectedOrder.data())
                if not match(pattern=r"^\d{6}/\d{2}/\d{4}/\d/\d$", string=order_id):
                    return False

                # Add validated data to `self.selectedOrder`
                self.selectedOrder = {
                    "length": length,
                    "quantity": quantity,
                    "diameter": diameter,
                    "order_id": order_id,
                    "customer_name": customer_name
                }
                return True
            else:
                return False
        except Exception:
            return False

    # Run proccess
    def runProccess(self):
        # Final check input check
        if not self.check_input():
            self.alert("Błędne dane wejściowe",
                       "Wprowadzone dane nie są poprawne.")
            logger.error("Wrong input data")
            return
        if self.machine_control.is_motor_on():
            self.alert("Maszyna jest w ruchu.",
                       "Wyłącz silnik nawijarki przed rozpoczęciem.")
            logger.error("The machine was running before")
            return
        if not self.machine_control.is_in_zero_positon():
            self.alert("Bęben wyciągarki jest w złej pozycji",
                       "Przywróć bęben do pozycji zerowej.\n PAMIĘTAJ O ODCZEPIENIU LINKI OD BĘBNA PRZED PRZYWRACANIEM.")
            logger.error("Winder drum is in bad position")
            return
        if self.selectedOrder:
            logger.success(
                "Successfully run `winding_in_progress` by 'tab_manual_winding'")
            self.winding_dialog = WindingInProgressDialog(
                parent_class=self.parent_class,
                ui_templates_dir=self.ui_templates_dir,
                machine_control=self.machine_control,
                buzzer=self.buzzer,
                encoder=self.encoder,
                length_target=self.selectedOrder['length'],
                quantity_target=self.selectedOrder['quantity'],
                diameter=self.selectedOrder['diameter'],
                order_id=self.selectedOrder['order_id'],
                customer_name=self.selectedOrder['customer_name']
            )

            self.winding_dialog.rejected.connect(self.on_rejected)
            self.winding_dialog.accepted.connect(self.on_accepted)
            self.winding_dialog.exec_()
        else:
            self.alert("Nie wybrano zlecenia",
                       "Wybierz zlecenie przed rozpoczęciem")

    def on_accepted(self):
        logger.success("Successfully done `winding_in_progres` dialog process")
        del self.winding_dialog
        self.run_pushButton.setDisabled(True)

    def on_rejected(self):
        logger.warning(
            "Done before the expected ending, `winding_in_progres` dialog process")
        del self.winding_dialog
        print("Process canceled and obj is deleted")

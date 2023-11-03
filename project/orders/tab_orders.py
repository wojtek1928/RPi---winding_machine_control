from datetime import datetime, timedelta
import os
from enum import Enum, auto
from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow, QWidget, QTreeView, QPushButton
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QColor, QFont
from PyQt5.QtCore import QModelIndex, QThreadPool
from loguru import logger
from regex import match

from machine_control import MachineControl
from encoder import Encoder
from buzzer import Buzzer
from LOGS.error_handling import ErrorDialog
from label_printing.print import ZebraPrinter
from winding_in_progres import WindingInProgressDialog
from db.db import OrdersDBActions, OrdersDBWorker
from db.read_csv import Row
from orders.confirmation_DONE_run import ConfirmationDONERun
from orders.confirmation_mark_as_DONE import ConfirmationMarkAsDone
from orders.confirmation_print_label import ConfirmationPrintLabel
from orders.order import Order, OrderStatus


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


class OrdersTab(QWidget):
    # Flag which switch actions for `pushButton_run`
    __confirm_before_run: bool = False
    # Flag which switch actions for `pushButton_func` if True then print label else set label as DONE
    __print_mode: bool
    # List which contains oreders as `Order` objects list
    orders: list[Order] = []

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
        self.__buzzer = buzzer
        self.__parent_class = parent_class
        self.ui_templates_dir = ui_templates_dir

        uic.loadUi(os.path.join(
            ui_templates_dir, "orders_tab.ui"), self)
        # Add tab to main window
        parent_class.tabWidget.addTab(self, "Zlecenia")

        # Flag for reading orders
        self.only_done: bool = False
        self.refreshOrders()

        # Define `pushButton_run` and handle clicked event
        self.pushButton_run: QPushButton
        self.pushButton_run.clicked.connect(self.onRunBtnClicked)

        # Define `pushButton_toggleOrders` and handle clicked event
        self.pushButton_toggleOrders: QPushButton
        self.pushButton_toggleOrders.clicked.connect(self.toggleOrders)
        self.pushButton_toggleOrders.setStyleSheet("color: black;")

        # Define `pushButton_refresh` and handle clicked event
        self.pushButton_refresh: QPushButton
        self.pushButton_refresh.clicked.connect(self.refreshOrders)
        self.pushButton_refresh.setStyleSheet("color: black;")

        # Define `pushButton_func` and handle clicked event
        self.pushButton_func: QPushButton
        self.pushButton_func.clicked.connect(self.onFuncBtnClicked)
        self.pushButton_func.setStyleSheet("color: black;")
        # Default hide `pushButton_func`
        self.pushButton_func.hide()

        # Define `treeView` and fill it with data
        self.treeView: QTreeView
        self.treeModel = QStandardItemModel()

        # Style VerticalScrollBar
        with open("project/orders/ScrollBarVerticalStyle.txt", "r")as f:
            scrollBarStyle = f.read()
        self.treeView.verticalScrollBar().setStyleSheet(scrollBarStyle)
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
        # self.show_orders()

        # except Exception as e:
        #     print("Module OrdersTab initialization failed.", e, sep='\n')

    def show_orders(self):
        for order in self.orders:
            if self.only_done and order.status != OrderStatus.DONE:
                continue
            elif not self.only_done and order.status == OrderStatus.DONE:
                continue
            else:
                color = None
                status_label = ""
                if order.status == OrderStatus.INTERRUPTED:
                    color = QColor('#aa0000')
                    status_label = "Przerwane"
                elif order.status == OrderStatus.DONE:
                    color = QColor('#00aa00')
                    status_label = "Wykonane"
                elif order.status == OrderStatus.TODO:
                    color = QColor('#ffaa00')
                    status_label = "Do wykonania"

                # Assign order_id and status
                order_item = TreeItem(
                    order.order_id,
                    set_bold=True,
                    font_size=24,
                    color=color,
                    set_enabled=True
                )
                status = TreeItem(
                    status_label,
                    color=color
                )
                # Assign customer_name
                customer_name_label = TreeItem(order.customer_name_label)
                customer_name = TreeItem(order.customer_name, set_bold=True)
                order_item.appendRow([customer_name_label, customer_name])
                # Assign quantity
                quantity_label = TreeItem(order.quantity_label)
                quantity = TreeItem(f"{order.quantity}", set_bold=True)
                order_item.appendRow([quantity_label, quantity])
                # Assign length
                length_label = TreeItem(order.length_label)
                length = TreeItem(f"{order.length}", set_bold=True)
                order_item.appendRow([length_label, length])
                # Assign diameter
                diameter_label = TreeItem(order.diameter_label)
                diameter = TreeItem(f"{order.diameter}", set_bold=True)
                order_item.appendRow([diameter_label, diameter])

                if order.production_time:
                    # Assign production_time if exist
                    production_time_label = TreeItem(
                        order.production_time_label)
                    production_time = TreeItem(
                        order.production_time, set_bold=True)
                    order_item.appendRow(
                        [production_time_label, production_time])

                if order.done_date:
                    # Assign done_date if exist
                    done_date_label = TreeItem(order.done_date_label)
                    done_date = TreeItem(order.done_date, set_bold=True)
                    order_item.appendRow([done_date_label, done_date])

                self.rootNode.appendRow([order_item, status])

    def onItemExpansion(self, index: QModelIndex):
        """
        Checks if expanded row is selected
        """
        item = self.treeModel.itemFromIndex(index)
        item.setSelectable(True)
        selectedIndexes = self.treeView.selectedIndexes()
        if selectedIndexes and self.treeView.selectedIndexes()[0] == index:
            self.enable_actions()

    def onItemCollapse(self, index: QModelIndex):
        """
        Checks if collapsed row is selected, if is then disable `run_pushButton`
        """
        item = self.treeModel.itemFromIndex(index)
        item.setSelectable(False)
        selectedIndexes = self.treeView.selectedIndexes()
        if not selectedIndexes or self.treeView.selectedIndexes()[0] == index:
            self.enable_actions(False)

    def onSelection(self, selected: QModelIndex):
        """
        Checks if selected row is expanded, if so, then enable `run_pushButton`, if not, disable
        """
        if self.treeView.isExpanded(selected):
            self.enable_actions()
        else:
            self.enable_actions(False)

    def enable_actions(self, enable: bool = True):
        if enable:
            self.pushButton_run.setEnabled(True)
            if self.check_input():
                if self.selectedOrder.status == OrderStatus.DONE:
                    # Enable rerun confirmation
                    self.__confirm_before_run = True
                    # Enable printing for selected order
                    if (os.getenv("PRINT_LABELS", 'False') == 'True'):
                        self.__print_mode = True
                        self.pushButton_func.setText("Wydrukuj etykietę")
                        self.pushButton_func.show()

                else:
                    # Disable run confirmation
                    self.__confirm_before_run = False
                    # Enable setting as DONE for selected order
                    self.__print_mode = False
                    self.pushButton_func.setText("Przenieś do wykonanych")
                    self.pushButton_func.show()
        else:
            self.pushButton_run.setDisabled(True)
            self.pushButton_func.hide()

    def onRunBtnClicked(self):
        """
        Function which handles `clicked` event of `pushButton_run` 
        """
        if self.__confirm_before_run:
            self.confirm_rerun()
        else:
            self.runProcess()

    def onFuncBtnClicked(self):
        """
        Function which handles `clicked` event of `pushButton_run` 
        """
        if self.__print_mode:
            self.confirm_print()
        else:
            self.confirm_mark_as_DONE()

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

    def confirm_rerun(self):
        confirmation = ConfirmationDONERun(
            self,
            self.ui_templates_dir,
            self.selectedOrder
        )
        confirmation.accepted.connect(self.runProcess)
        confirmation.exec_()

    def confirm_mark_as_DONE(self):
        def accepted():
            self.submit_output_to_ordersDB(True, self.selectedOrder)

        confirmation = ConfirmationMarkAsDone(
            self,
            self.ui_templates_dir,
            self.selectedOrder
        )
        confirmation.accepted.connect(accepted)
        confirmation.exec_()

    def confirm_print(self):
        def print_label():
            try:
                printer = ZebraPrinter(
                    self.selectedOrder.order_id,
                    self.selectedOrder.customer_name,
                    self.selectedOrder.length,
                    self.selectedOrder.diameter
                )
                printer.print_label()
                logger.info("Additional label was added to printing queue")
            except Exception as e:
                logger.error("Additional label printing failed")
                alert = ErrorDialog(
                    self.__parent_class,
                    "Błąd drukowania etykiety",
                    "Sprawdź czy drukarka jest poprawnie podłączona i czy jest włączona.",
                    self.__buzzer,
                    True
                )
                alert.rejected.connect(print_label)
                alert.exec()

        confirmation = ConfirmationPrintLabel(
            self,
            self.ui_templates_dir,
            self.selectedOrder
        )
        confirmation.accepted.connect(print_label)
        confirmation.exec_()

    def refreshOrders(self):
        # Disable `pushButton_refresh`
        self.pushButton_refresh.setDisabled(True)

        def after(results: list):
            # Clean treeView
            self.treeModel.removeRows(0, self.treeModel.rowCount())
            # Show records
            self.orders = [Order(**result) for result in results]
            self.show_orders()
            logger.info("Orders was refershed")
            # Enable `pushButton_refresh`
            self.pushButton_refresh.setEnabled(True)

        def error(err_title: str = None, err_desc: str = None):
            # Enable `pushButton_refresh`
            self.pushButton_refresh.setEnabled(True)
            self.alert(err_title, err_desc)

        # Thread definition
        pool = QThreadPool.globalInstance()
        worker = OrdersDBWorker(OrdersDBActions.read_csv_and_update_db)
        # Done signal handling
        worker.signals.done.connect(after)
        # Error signal handling
        worker.signals.error.connect(error)
        # Set action on thread start
        worker.signals.started.connect(worker.run)
        # Start thread
        pool.start(worker)

    # Alert handlingfunction

    def alert(self, err_title, err_desc):
        alert = ErrorDialog(self.__parent_class, err_title,
                            err_desc, self.__buzzer)
        alert.exec()

    def check_input(self):
        try:
            if self.treeView.currentIndex():
                # Get id of selected order
                order_id = self.treeView.currentIndex().data()
                # Find order with order_id in orders list
                selectedOrder: Order = next(
                    (sub for sub in self.orders if sub.order_id == order_id), None)
                # Make validation and necessary types conversions
                # Read and valid `length`
                if selectedOrder.length <= int(os.getenv('START_LENGHT')):
                    return False
                # Read and valid `quantity`
                if selectedOrder.quantity <= 0:
                    return False
                # Read and valid `diameter`
                if selectedOrder.diameter <= 0:
                    return False
                # Read and valid `order_id`
                if not match(pattern=r"^\d{6}/\d{2}/\d{4}/[a-zA-Z0-9/]{3,5}$", string=selectedOrder.order_id):
                    return False

                # Add validated data to `self.selectedOrder`
                self.selectedOrder = selectedOrder
                return True
            else:
                return False
        except Exception as e:
            # Make log if anything went wrong and return False
            logger.error(e)
            return False

    # Run process
    def runProcess(self):
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
                parent_class=self.__parent_class,
                ui_templates_dir=self.ui_templates_dir,
                machine_control=self.machine_control,
                buzzer=self.__buzzer,
                encoder=self.encoder,
                length_target=self.selectedOrder.length,
                quantity_target=self.selectedOrder.quantity,
                diameter=self.selectedOrder.diameter,
                order_id=self.selectedOrder.order_id,
                customer_name=self.selectedOrder.customer_name
            )

            self.winding_dialog.rejected.connect(self.on_rejected)
            self.winding_dialog.accepted.connect(self.on_accepted)
            self.winding_dialog.exec_()
        else:
            self.alert("Nie wybrano zlecenia",
                       "Wybierz zlecenie przed rozpoczęciem")

    def on_accepted(self):
        self.submit_output_to_ordersDB(success=True)

    def on_rejected(self):
        self.submit_output_to_ordersDB(success=False)

    def submit_output_to_ordersDB(self, success: bool, order: Order = None):
        # Disable `pushButton_run` and `pushButton_refresh`
        self.pushButton_run.setDisabled(True)
        self.pushButton_refresh.setEnabled(True)
        if order is None:
            # Capture data from `winding_dialog`
            order_id = self.winding_dialog.order_id
            production_time = self.winding_dialog.final_execution_time
            done_date = datetime.now().strftime("%Y-%m-%d %H:%M")
            # Delete `winding_dialog` object
            del self.winding_dialog
            logger.info("winding_dialog was deleted.")
        else:
            # Insert data from order object to db
            order_id = order.order_id
            production_time = order.production_time_sec if order.production_time_sec else None
            done_date = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Define signals actions
        def after(results=list[Row]):
            # Clean treeView
            self.treeModel.removeRows(0, self.treeModel.rowCount())
            # Refresh records
            self.refreshOrders()
            logger.info("Orders were updated")
            # Enable `pushButton_refresh`
            self.pushButton_refresh.setEnabled(True)

        def error(err_title: str = None, err_desc: str = None):
            # Enable `pushButton_refresh`
            self.pushButton_refresh.setEnabled(True)
            logger.error(
                "Orders were NOT updated.")
            self.alert(err_title, err_desc)

        # Thread definition
        pool = QThreadPool.globalInstance()
        if success:
            worker = OrdersDBWorker(
                OrdersDBActions.set_done_status, order_id, production_time, done_date)
        else:
            worker = OrdersDBWorker(
                OrdersDBActions.set_interrupted_status, order_id, production_time, done_date)
        # Done signal handling
        worker.signals.done.connect(after)
        # Error signal handling
        worker.signals.error.connect(error)
        # Set action on thread start
        worker.signals.started.connect(worker.run)
        # Start thread
        pool.start(worker)

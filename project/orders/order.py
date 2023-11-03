from enum import Enum


class OrderStatus(str, Enum):
    DONE = "DONE"
    INTERRUPTED = "INTERRUPTED"
    TODO = "TODO"


class Order:
    """
    Order
    --
    Class which takes 
    """
    order_id: str
    order_id_label = "Nr zlecenia:"

    status: OrderStatus
    status_label = "Status:"

    customer_name: str
    customer_name_label = "Nazwa klienta:"

    quantity: int
    quantity_label = "Ilość sztuk:"

    length: int
    length_label = "Długość [mm]:"

    diameter: float
    diameter_label = "Średnica [mm]:"

    production_time: str = None
    production_time_sec: float = None
    production_time_label = "Czas wykonania:"

    done_date: str = None
    done_date_label = "Data wykonania:"

    def __init__(
            self,
            order_id,
            status,
            quantity,
            length,
            diameter,
            customer_name,
            production_time,
            done_date
    ) -> None:
        self.order_id = str(order_id).strip()
        # Status
        self.status = OrderStatus(status)
        # Customer name
        self.customer_name = str(customer_name).strip()
        # Quantity
        self.quantity = int(quantity)
        # Length
        self.length = int(length)
        # Diameter
        self.diameter = float(diameter)
        # Production time
        if production_time:
            self.production_time_sec = float(production_time)
            production_time_sec = int(production_time)
            self.production_time = f"{production_time_sec//3600}h {production_time_sec//60}m {production_time_sec%60}s"
        # Done date
        if done_date:
            self.done_date = str(done_date)

    def __str__(self):
        return \
            f"""{self.order_id_label} {self.order_id}
{self.customer_name_label} {self.customer_name}

{self.quantity_label} {self.quantity}
{self.length_label} {self.length}
{self.diameter_label} {self.diameter}

{self.production_time_label} {self.production_time}
{self.done_date_label} {self.done_date}"""

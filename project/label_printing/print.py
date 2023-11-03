import zpl
import cups
from zebra import Zebra
from datetime import datetime

# Install cups, cups-bsd, and lpr to use
# sudo apt-get install cups
# sudo apt-get install cups-bsd
# sudo apt-get install lpr


class ZebraPrinter:
    label_width = 90
    label_height = 36

    def __init__(self, order_id: str, customer_name: str, length: int, diameter: float) -> None:
        self.order_id = order_id
        self.customer_name = customer_name
        self.length = length
        self.diameter = diameter

    def get_label(self) -> str:
        """
        Returns zpl label to print
        """
        # Define Label height[mm], width[mm], dpmm[dots per mm]12 = 300dpi
        label = zpl.Label(self.label_height, self.label_width, dpmm=12)
        v_begin = 2  # Vertical offset for first words x orgin

        h_field_first_line = 12  # y orgin of first field
        h_line_step = 6  # space betwen lines

        def line(num: int) -> int:
            """
            Returns y orgin depends on line number
            """
            return h_field_first_line + num*h_line_step

        # Set UTF-8 encoding
        label.change_international_font(28)

        # Title `NITUS` word
        label.origin(2, 2)
        label.set_default_font(8, 0, '0')
        label.write_text("NITUS")
        label.endorigin()

        # Set default font for labels
        label.set_default_font(5, 0, '0')
        # Field `Nr zam.:`
        label.origin(v_begin, line(0))
        label.write_text(f"Nr zam.: {self.order_id}")
        label.endorigin()

        # Field `Klient:`
        label.origin(v_begin, line(1))
        label.write_text(f"Klient: {self.customer_name}")
        label.endorigin()

        # Field `Długość:`
        label.origin(v_begin, line(2))
        label.write_text(f"Długość: {self.length} mm")
        label.endorigin()

        # Field `Średnica:`
        label.origin(v_begin, line(3))
        label.write_text(f"Ø: {self.diameter} mm")
        label.endorigin()

        # print(label.dumpZPL())
        # label.preview()

        return label.dumpZPL()

    def print_label(self):
        printer = Zebra()
        # Get available zebra printers queues (should find one)
        printer_queue = printer.getqueues()
        try:
            # Check printer availability
            conn = cups.Connection()
            printers = conn.getPrinters()
            if printers['Zebra_ZD421']['printer-state-message'] == "Unplugged or turned off":
                raise Exception("Printer unplugged or turned off")
            # Set first founded queue as output
            printer.setqueue(printer_queue[0])
        except Exception as e:
            raise e
        # Print ZPL code from the `get_label()` function.
        # Usage of `encode("utf-8")` is needed due to the presence of Polish special characters.
        printer.output(self.get_label().encode("utf-8"))


if __name__ == '__main__':
    p = ZebraPrinter(
        order_id="123456/12/1234/1/1",
        customer_name="Jan Kowalski",
        length=10500,
        diameter=3.2
    )
    p.get_label()

# Winding machine steering
The purpose of this project was to make a new control panel for the machine that prepers steel ropes for segment gates. The previous solution was simpler, not accurate, and user-unfriendly, it had no connection to the database, and labels were written by hand. In fact, this machine without this new control was unusable, and the worker decided not to use it as he could manually make rope faster than with a machine.

Check out my video on YouTube and see the result in production: https://youtu.be/TXwPDj5fDOA

## Reasons for making this project
First of all, the ropes used in this type of gate require two steel ropes, which should be equal in length. The previous measuring solution had a precision of `10 cm', and at the beginning of winding, the first increment of measured length appeared at different moments.
The second reason is that the winder motor is run with a simple relay (an inverter would be a much better choice, but it was not installed because of costs). So there is no possibility of slowing down the engine near the end of the winding process.
So at the end, making ropes with the same length was almost impossible, and the worker had to measure each rope by hand and validate its final length. Most of those rope pairs had different lengths.
Moreover, labels were printed in advance and filled out by hand, which also took time for the worker.

## Hardware modification

### Control unit and printing:
- Raspberry Pi4
- IPS LCD touch screen 10.1'' (B) 1280x800px
- Relay module signaling the necessary signals to the machine
- Handmade connection board that connects all the signal to the Rasberry Pi
- Steel casing designed and manufactured by me for this application

### Sensors added and reused in this machine:
- incremental encoder with a resolution of 7200 [PPR] for measuring the rope length
- Hall sensor for setting the zero position of the drum
- pressure switch for checking the presence of air pressure
- addtion of wiring to the previously installed motor switches to detect the state of the winder motor
- using the previous present hall sensor, which detects guilotine up

### Printing:
- Zebra ZD421 label printer

## Why Python and what about safety?
I decided to use Python because I could easily write this HMI (Human Machine Interface) in a relatively short time period (approximately 2 months). I am aware that for purposes like that, C or C++ would be much more reliable and faster in terms of operation time. Finally, I do not use those because this machine is a one-time project. Moreover, this machine has built-in all necessary safety systems, so if my control panel fails, there is still a possibility to emergency stop working the machine.

### Mainly used libraries:
-  [pigpio](https://abyz.me.uk/rpi/pigpio/pigpiod.html) - GPIO operations
-  [PyQt5](https://www.riverbankcomputing.com/software/pyqt/) - interface
-  [loguru](https://github.com/Delgan/loguru) - system logs
-  [time](https://docs.python.org/3/library/time.html) - real-time operations
-  [zpl](https://github.com/cod3monk/zpl) - label definition
-  [zebra](https://pypi.org/project/zebra/) - communication with printer 
-  [sqlite](https://docs.python.org/3/library/sqlite3.html) - database connection
-  [csv](https://docs.python.org/3/library/csv.html) - retrieving data from CSV files

## Database
I used the SQLite database because of its simplicity. This machine is the only client to this database and uses only one table, which contains several columns:
-  `order_id` as primary key,
-  `status` of order,
- `customer_name`,
-  `done_date` is an optional column which stores date of rope production,
-  `production_time` optional column, which contains time of order production,
-  `created_at` datetime field with timestamp of order db insertion,
Ropes params:
-  `quantity`,
-  `length`,
-  `diameter`,

## Communication with the machine and data processing
The communication system that allows the production management team to update orders on the machine is based on the exchange folder. This system is modeled on communication with other CNC machines used by this company.

### How does it work?
1. Someone sends orders through a management system program as a single or series of CSV files.
2. Files are saved in the `TEMP` swap folder.
3. The data is stored there until it is saved to the database.
4. After processing and saving the data in proper form to the database, each CSV file is moved to the `ARCHIVE` directory with a modified timestamp name. All previously saved data is stored in this directory.

Each time you run or refresh orders from the HMI level, this procedure is repeated if new CSV files appear in the `TEMP` directory.

## Human Machine InterFace (HMI)
HMI is made with the `PyQt5` library and, in fact, is a full-screen frameless autostart application. The result of that is that there is no possibility of leaving this application when the only interface to Rasberry is a touch screen.

### The interface contains three tabs:
1. `Zlecenia`(orders_tab) - where the worker can choose an order to execute. Additional workers can see completed orders, rerun them, or print additional labels. Each order can be canceled, and then it is still in the to-do section, but now it is marked with a red color as interrupted. Each order from the to-do section can be moved manually to the done section without running the winding process. The second option is to run the winding process, and after it is complete, the order is automatically marked as done.
2. `Sterowanie ręczne` (manual_steering_tab) -  in this tab, the user can manually manipulate the machine with buttons that are digital copies of previous physical buttons. Also, there is the possibility to run a measuring process with an encoder, and the result is displayed as a number of milimeters[mm]. If the winder motor is running or the measuring process is running and not reset, the rest of the interface is disabled.
3. `Wprowadznie ręczne` (manual_insert_tab) - in this tab, the user can manually insert an order to run and automatically save it to the database. Inserted data is dynamically validated, and if the data is correct, the user can run a winding process. At the beginning of a process, an order is saved to DB as `todo`, and after canceling or completing the order, it is saved to DB as `interrupted` or `done`.

Menu bar contains:
--
- `Edycja` (Edit) - there is one action setting which opens the settings tab,
- `Pomoc` (Help) - there are two options: help and information about the program.

#### Settings
The user can set those options, which are stored in the`.env` file and loaded as environmental variables on each application run:
- `PRINT_LABELS` - boolean for disabling or enabling printing labels,
- `PRINT_LABEL_EVERY_OTHER_ROPE` - boolean for disabling or enabling printing labels for every other rope,
- `START_LENGHT` - distance from guillotine to hook on winder drum [milimeters],
- `STOP_OFFSET` - compensation of winder motor interia before stop. It means that the motor is turned off a certain distance before the end of the rope [milimeters],
- `GUILLOTINE_DOWN_TIME` - guillotine down time during the atomatic rope cut [seconds],
- `GUILLOTINE_UP_TIME` - guillotine up time during atomatic rope cut [seconds],
- `TIME_TO_SEARCH_FOR_ZERO` - time for looking for zero drum position. If not found in the given number of seconds, then the motor is stopped and an error is raised [seconds],
- `BUZZER_SIGNALS` - bool for enabling or disabling buzzer sounds during the winding process,
- `CONFIRM_NEW_LINE_TIME` - time for confirmation button needs to be pressed to confirm running process [seconds].

### Winding Process
The winding process is a dialog that is frameless and is executed as a full-screen widget.

This widget changes its functionality depends in which state it is.  There is eleven states:
- `paused` - user can move to this state from each state. Except `summary` and `next_rope`, the user go to `cancel` state or continue the previously paused state,
- `cancel` - user can move to this state from each state. Except `summary` and `next_rope`, the user can cancel the winding process and go `summary` state.
- `winding` - in this state, the winder motor is running. In the background, the `Monitor`, object checks the machine state, and if something goes wrong, it raises an error, and the state is changed to `winding_fail`. If not, then `reset_position` state goes next.
- `winding_fail` - state, which is set when any errors are raised in the `winding` state. The user can set the `winding` state again or the `cancel` state.
- `cut_rope` - in this state, the guilotine is pressed and released. If something goes wrong, then the state is changed to `cut_rope_fail`.  If not, then `reset_position` state goes next.
- `cut_rope_fail` - state, which is set when any errors are raised in the `cut_rope` state. The user can set the `cut_rope` state again or the `cancel` state.
- `reset_position` - in this state, the winder drum is bringing itself back to its zero position. If something goes wrong, then the state is changed to `reset_position_fail`.  If not, then the `next_run_confirmation` or `summary` state goes next, depending on the quantity of the made ropes.
- `reset_position_fail` - state, which is set when any errors are raised in the `reset_position` state. The user can set the `reset_position` state again or the `cancel` state.
- `next_run_confirmation` - in this state user has three options. First is initialize the confirmation to run next rope, state is changed to `next_run`. Second option is to change state back to `reset_position_fail` this options is needed due to hardware malfunctions. Third option is to set `cancel` state.
- `next_rope` - this state is responsible for the confirmation of the next run. If the user is holding the `first_pushbutton` for `CONFIRM_NEW_LINE_TIME` seconds, then the state is changed to `winding`. If user releases the button earlier, then state is changed back to `next_run_confirmation`
- `summary` - this state can be reached from the `cancel` state or `reset_position`. If the previous state was `cancel` then the dialog is rejected and the user goes back to the `manual_insert_tab` or `orders_tab` depending on which was the initiator.

## Label printing
The following information about the order is contained on the label:
- `order_id`
- `length`
- `quantity`
- `diameter`

Labels could be printed in those situations and only when `PRINT_LABELS` is True:
- user wants to print label in `orders_tab`
- if option `PRINT_LABEL_EVERY_OTHER_ROPE` is True, then label is printed on every other rope,
- if user cancel the winding process and quantity of ropes is greater than 0,
- at the end of winding processes
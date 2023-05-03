## common module

### feedback.py
Feedback class, used to define the attributes required when users mark tasks as finished.

### group.py
Group class

### help_request.py
Help-request class, also defining a method for converting the help-request to a payload that can be transmitted over MQTT.

### io_utils.py
Utility functions for importing data from the data directory

### module.py
Module class

### mqtt_utils.py
MQTT config file with helper methods for parsing incoming messages.
Also defines topics, message types and broker details. Includes a
RequestWrapper class used for standardizing the messages, to facilitate 
parsing.
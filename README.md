## TTM4115 - Final Project, Team 01

### 1. Prerequisites
- Python 3.7+ installed
- Working internet connection (to connect to the MQTT broker)

### 2. Installation / setup
- Create virtual environment, e.g. using the command
`python3 -m venv ./venv` while in the root folder
- Active newly created virtual environment, e.g. using the command `source venv/bin/activate` on Unix/MacOS (or `./venv/Scripts/activate` on Windows)
- Install required packages (specified in requirements.txt) to the virtual environment, e.g. using the command `pip install -r requirements.txt`

### 3. Starting the application from terminal
##### 3.1: Student client
Student client can be started by completing all installation steps, and running the command
`python3 -m code_student.main` while in the project root (komsys-project directory).

##### 3.2: TA client
Student client can be started by completing all installation steps, and running the command
`python3 -m code_teaching_assistant.main` while in the project root (komsys-project directory).

##### 3.3: Setup application
We have created a setup-application for configuring groups and modules in the ´/data´ directory.
This application can be started by running
`python3 -m setup.main` while in the project root (komsys-project directory).


### 4. Project structure
`/code_student`: Code for the student client

`/code_teaching_assistant`: Code for the TA client

`/common`: Common functions used by both the student- and TA-client. Contain util-functions and classes used throughout the project.

`/setup`: Code for the configuration-application

`/data`: .json files containing group- and module-information, and the sound file used for the notification-sound.

### 5. Contact
If you have any issues with executing the project, feel free to contact Joachim Maksim at `joachimmaksim(at)gmail.com`.
# Test driver.  Run py-holmes on each unittest bug for a specific project in the BugsInPy dataset and compile all their
# reports in a log file.
# Should be called with a single positional argument: the name of the project within the BugsInPy dataset to run tests on


# Get project_to_test
project_to_test=$1


# Determine log name by finding the first number that isn't taken
counter=0
while $([ -f log${counter}.log ])
do
  counter=$(( ${counter} + 1 ))
done
log_name="log${counter}.log"


# Set up logging file; NOTE THAT THIS WIPES PREVIOUS CONTENT FROM THE FILE
:> "${log_name}"


# Make note of log path and log directory path
log_directory_path="$(pwd)"
log_path="$(pwd)/${log_name}"

# Make note of the folder above the py-holmes root folder
cd ..
cd ..
cd ..
folder_above_py_holmes_root_folder="$(pwd)"
cd "$log_directory_path"


# Add BugsInPy to the command path
cd BugsInPy
current_directory=$(pwd)
export PATH=$PATH:"$current_directory"/framework/bin


# Get array of checkout commands, skipping commands whose corresponding run_test.sh isn't a [unittest and not pytest].
# Get array of project folder names
cd projects
folders=( "$(ls -d */)" )   # Beware, this approach does not work for folder names with spaces in them
SAVEIFS=$IFS
IFS=$'\n'
folders=($folders)
IFS=$SAVEIFS
# Remove trailing "/" from each name in folders
for ii in "${!folders[@]}"
do
  folders[ii]=$(echo "${folders[$ii]}" | cut -d '/' -f 1)
done

# Get array of checkout commands
declare -a checkout_commands
for folder in "${folders[@]}"
do
  cd "$folder"
  cd bugs
  folders_in_bugs=( "$(ls -d */)" )
  SAVEIFS=$IFS
  IFS=$'\n'
  folders_in_bugs=($folders_in_bugs)
  IFS=$SAVEIFS
  # Remove trailing "/" from each name in folders_in_bugs
  for ii in "${!folders_in_bugs[@]}"
  do
    folders_in_bugs[ii]=$(echo "${folders_in_bugs[$ii]}" | cut -d '/' -f 1)
  done
  for folder_in_bugs in "${folders_in_bugs[@]}"
  do
    cd "$folder_in_bugs"
    run_test_file_content=$(<run_test.sh)
    if [[ $run_test_file_content == *"unittest"*  &&  $run_test_file_content != *"pytest"* ]]   # If "unittest" is in run_test_file_content and "pytest" is not...
    then
      component_0="bugsinpy-checkout -p "
      component_1="$folder"
      component_2=" -v 0 -i "
      component_3="$folder_in_bugs"
      component_4=" -w "
      component_5="$folder_above_py_holmes_root_folder"
      component_6="/TEMP/projects"
      checkout_commands+=("$component_0$component_1$component_2$component_3$component_4$component_5$component_6")
    fi
    cd ..
  done
  cd ..
  cd ..
done


# Run py-holmes on each BugsInPy failing test, skipping tests that don't pertain to project_to_test
# Go to the correct directory for executing checkouts (BugsInPy/)
cd ..
# Remember this directory for later
directory_to_checkout_from=$(pwd)
# Begin execution
for command in "${checkout_commands[@]}"
do
  if [[ "${command}" == *"${project_to_test}"* ]]
  then
    echo "%%%%%%%%%%%%%%%%%%%%%%%% BEGIN NEW TEST %%%%%%%%%%%%%%%%%%%%%%%%"
    echo "%%%%%%%%%%%%%%%%%%%%%%%% BEGIN NEW TEST %%%%%%%%%%%%%%%%%%%%%%%%" >> "$log_path"
    echo "COMMAND for this test is $command"
    echo "COMMAND for this test is $command" >> "$log_path"

    # Checkout to that bug
    echo "CHECKING out..."
    $command

    # Go to the directory we checked out to
    echo "GOING to the directory we checked out to..."
    cd "$folder_above_py_holmes_root_folder"
    cd TEMP
    cd projects
    IFS=' ' read -r -a command_split <<< "$command"
    name_of_project=${command_split[2]}
    cd $name_of_project

    # Run bugsinpy-test and put the result in the log file
    echo "RUNNING bugsinpy-compile..."
    bugsinpy-compile
    echo "EXECUTING bugsinpy-test and putting the result in the log file..."
    echo "### RUNNING BUGSINPY-TEST ###" >> "$log_path"
    bugsinpy-test >> "$log_path"

    # Copy py-holmes into this same directory
    cd "$folder_above_py_holmes_root_folder"
    part_1="TEMP/projects/"
    part_2="$project_to_test"
    cp -rT py-holmes "$part_1$part_2"

    # Reinstall py_holmes' directories, just in case
    cd TEMP
    cd projects
    cd "$project_to_test"
    pip install -r ph_requirements_shallow.txt

    # Install the requirements.txt file in the folder checked out to, if one exists.
    # (This is necessary because not all the required packages remain installed
    # after BugsInPy does its thing)
    if $([ -f requirements.txt ])
    then
      pip install -r requirements.txt
    fi

    # Run py-holmes on this test
    # Grab the original test command, which will be used by cli_call_creator.py
    run_test_file_content=$(<bugsinpy_run_test.sh)
    echo "RUN_TEST_FILE_CONTENT is ${run_test_file_content}"

    # Go to the same folder as cli_call_creator.py and use it to get the line to call py-holmes with
    echo "GETTING callsign from cli_call_creator.py..."
    cd ph_benchmarks
    cd ph_BugsInPy
    call_for_cli_call_creator="python cli_call_creator.py -p '${name_of_project}' -u '${run_test_file_content}'"
    call_for_py_holmes=$(eval "$call_for_cli_call_creator" 2>&1)
    echo "call_for_py_holmes is ${call_for_py_holmes}"
    echo "call_for_py_holmes is ${call_for_py_holmes}" >> "$log_path"

    # Go to py-holmes's directory, run py-holmes on the test, grab the report, and put it in the log file
    echo "MOVING to py-holmes's directory and running on the test..."
    echo "### RUNNING PY-HOLMES ###" >> "$log_path"
    cd ..
    cd ..   # Now we're in the py-holmes root directory
    report=$(eval "$call_for_py_holmes" 2>&1)
    py_holmes_exit_code=$?
    echo "$report" >> "$log_path"
    echo "EXITED PY-HOLMES WITH EXIT CODE ${py_holmes_exit_code}" >> "$log_path"

    # Return to directory for next checkout
    cd "$directory_to_checkout_from"
  fi
done

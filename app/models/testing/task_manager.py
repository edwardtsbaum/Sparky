# task_manager.py

import datetime

# In-memory task storage for demonstration purposes
tasks = {}
task_counter = 1

def add_task(description, due_date):
    global task_counter
    tasks[task_counter] = {
        'description': description,
        'due_date': due_date,
        'completed': False
    }
    task_id = task_counter
    task_counter += 1
    return f"Task added with ID {task_id}."

def delete_task(task_id):
    if task_id in tasks:
        del tasks[task_id]
        return f"Task {task_id} deleted."
    else:
        return f"Task {task_id} does not exist."

def list_tasks():
    if not tasks:
        return "No tasks available."
    task_list = "Current Tasks:\n"
    for id, details in tasks.items():
        status = "✔️" if details['completed'] else "❌"
        task_list += f"{id}. [{status}] {details['description']} (Due: {details['due_date']})\n"
    return task_list

def update_task(task_id, description=None, due_date=None):
    if task_id in tasks:
        if description:
            tasks[task_id]['description'] = description
        if due_date:
            tasks[task_id]['due_date'] = due_date
        return f"Task {task_id} updated."
    else:
        return f"Task {task_id} does not exist."

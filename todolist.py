import tkinter as tk
root=tk.TK()

root.title("To-do List")
root.geometry("400x500")
task_entry=tk.entry(root,width=30)
task_entry.pack(pady=10)

add_button=tk.Button(root,text="추가",width=10)
add_button.pack(pady=5)

task_listbox=tk.Listbox(root,width=40,height=15)
task_listbox.pack(pady=10)

delete_button=tk.Button(root,text="삭제",width=10)
delete_button.pack(pady=5)

complete_button=tk.Button(root,text="완료",width=10)
complete_button.pack(pady=5)

root.mainloop()
import tkinter as tk
import sqlite3
from tkinter import messagebox

class Todo:

    UNCHECKED = "☐ "
    CHECKED = "☑ "

    def __init__(self, root):
        self.root = root
        root.title("To-do List") #맨 위에 제목("To-do List")
        root.geometry("500x600") #사이즈 약간 넓게 조정

        #db세팅
        self.dbinfo = dict(
            host="34.27.84.32",    # 외부 MySQL 서버 주소로 수정!
            user="todo_user",
            password="mypass123",
            database="todo_db"
        )
        self.conn = sqlite3.connect("todo.db")
        self.cursor = self.conn.cursor()
        
        print(self.cursor.fetchone())

        self.cursor.execute("""
    CREATE TABLE IF NOT EXISTS todolists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task TEXT NOT NULL,
        completed INTEGER NOT NULL DEFAULT 0,
        sort_order INTEGER NOT NULL DEFAULT 0,
        priority INTEGER NOT NULL DEFAULT 5 
    )
""") #기본값 5로 지정
        try:
            self.cursor.execute("ALTER TABLE todolists ADD COLUMN sort_order INT NOT NULL DEFAULT 0")
            self.conn.commit()
        except Exception:
            pass

        self.listbox_task_ids = []
        self.deleted_item_stack = []

        self.setup_gui()
        self._ensure_sort_order()
        self.display_tasks()
        root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_gui(self):
        # 입력창
        self.task_entry = tk.Entry(self.root, width=40)
        self.priority_entry = tk.Entry(self.root, width=5)
        self.priority_entry.pack()
        self.priority_entry.insert(0, "5")
        self.task_entry.pack(pady=(15,5))
        self.task_entry.bind("<Return>", self.add_task)

        # 버튼 1줄: 추가/삭제/복구/새로고침
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=3)
        self.add_button = tk.Button(button_frame, text="추가", width=8, command=self.add_task)
        self.add_button.pack(side=tk.LEFT, padx=2)
        self.delete_button = tk.Button(button_frame, text="삭제", width=8, command=self.delete_task)
        self.delete_button.pack(side=tk.LEFT, padx=2)
        self.undo_button = tk.Button(button_frame, text="복구", width=8, command=self.undo_delete)
        self.undo_button.pack(side=tk.LEFT, padx=2)
        # 새로고침은 강제 DB 재연결 포함 (우회)
        self.refresh_button = tk.Button(button_frame, text="새로고침", width=8, command=self.force_refresh)
        self.refresh_button.pack(side=tk.LEFT, padx=2)

        # 버튼 2줄: 순서 이동
        order_frame = tk.Frame(self.root)
        order_frame.pack(pady=3)
        self.up_button = tk.Button(order_frame, text="↑ 위로", width=8, command=self.move_up)
        self.up_button.pack(side=tk.LEFT, padx=2)
        self.down_button = tk.Button(order_frame, text="↓ 아래로", width=8, command=self.move_down)
        self.down_button.pack(side=tk.LEFT, padx=2)

        # 리스트박스
        list_frame = tk.Frame(self.root)
        list_frame.pack(pady=(10,0), padx=10, fill=tk.BOTH, expand=True)
        self.task_listbox = tk.Listbox(self.root, width=50, height=18, selectmode=tk.EXTENDED)
        self.task_listbox.bind('<Double-Button-1>', self.toggle_complete)
        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=self.task_listbox.yview)
        self.task_listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill="y", in_=list_frame)
        self.task_listbox.pack(side=tk.LEFT, fill="both", expand=True, in_=list_frame)

    def display_tasks(self):
        self.task_listbox.delete(0, tk.END)
        self.listbox_task_ids.clear()
        try:
            self.cursor.execute("""
            SELECT id, task, completed, priority FROM todolists
            ORDER BY priority ASC, sort_order ASC
        """)
            for row in self.cursor.fetchall():
                task_id, task_text, completed_status, priority = row
                prefix = self.CHECKED if completed_status else self.UNCHECKED
                display_text = f"[{priority}] {prefix}{task_text}"
                self.task_listbox.insert(tk.END, display_text)
                self.listbox_task_ids.append(task_id)
                if completed_status:
                    self.task_listbox.itemconfig(tk.END, {'fg': 'gray'})
                elif priority <= 2:
                    self.task_listbox.itemconfig(tk.END, {'fg': 'red'})
                else:
                    self.task_listbox.itemconfig(tk.END, {'fg': 'black'})
        except sqlite3.Error as e:
            messagebox.showerror("DB 오류", f"할 일 목록을 불러오는 중 오류 발생: {e}")

    def force_refresh(self):
        # 새로고침 시 강제로 DB 연결/커서 다시 열기 (동기화)
        try:
            self.conn.close()
        except:
            pass
        self.conn = sqlite3.connect(**self.dbinfo)
        self.cursor = self.conn.cursor()
        self.display_tasks()
        self.root.update_idletasks()

    def add_task(self, event=None):
        task = self.task_entry.get()
        try:
            priority=int(self.priority_entry.get())
        except ValueError:
            messagebox.showwarning("경고","우선순위는 정수로 입력하세요.")
            return

        if task:
            try:
                self.cursor.execute("SELECT IFNULL(MAX(sort_order), 0) FROM todolists")
                max_order = self.cursor.fetchone()[0]
                self.cursor.execute("INSERT INTO todolists (task, sort_order, priority) VALUES (?, ?, ?)", (task, max_order + 1, priority))
                self.conn.commit()
                print(f"할 일 추가: {task} (우선순위 {priority})")
                self.task_entry.delete(0, tk.END)
                self.priority_entry.insert(0, "5")
                self.display_tasks()
            except sqlite3.connector.Error as e:
                messagebox.showerror("DB 오류", f"할 일 추가 중 오류 발생: {e}")
        else:
            messagebox.showwarning("경고", "할 일을 입력해주세요.")

    def delete_task(self):
        selected_indices = self.task_listbox.curselection()
        if selected_indices:
            for index in sorted(selected_indices, reverse=True):
                task_id = self.listbox_task_ids[index]
                try:
                    self.cursor.execute("SELECT id, task, completed, sort_order FROM todolists WHERE id=?", (task_id,))
                    deleted_row = self.cursor.fetchone()
                    if deleted_row:
                        self.deleted_item_stack.append(deleted_row)
                        self.cursor.execute("DELETE FROM todolists WHERE id=?", (task_id,))
                        self.conn.commit()
                except sqlite3.Error as e:
                    messagebox.showerror("DB 오류", f"할 일 삭제 중 오류 발생: {e}")
            self._reorder_sort_orders()
            self.display_tasks()
        else:
            messagebox.showwarning("경고", "삭제할 항목을 선택해주세요.")

    def undo_delete(self):
        if self.deleted_item_stack:
            last_deleted = self.deleted_item_stack.pop()
            _, task, completed, _ = last_deleted
            try:
                self.cursor.execute("SELECT IFNULL(MAX(sort_order), 0) FROM todolists")
                max_order = self.cursor.fetchone()[0]
                self.cursor.execute("INSERT INTO todolists (task, completed, sort_order) VALUES (?, ?, ?)", (task, completed, max_order + 1))
                self.conn.commit()
                self.display_tasks()
            except sqlite3.Error as e:
                messagebox.showerror("DB 오류", f"삭제 복구 중 오류 발생: {e}")
        else:
            messagebox.showinfo("안내", "복구할 항목이 없습니다.")

    def toggle_complete(self, event=None):
        selected = self.task_listbox.curselection()
        if not selected:
            return
        selected_listbox_index = selected[0]
        taskID_toTOGGLE = self.listbox_task_ids[selected_listbox_index]
        try:
            self.cursor.execute("SELECT id, completed FROM todolists WHERE id=?", (taskID_toTOGGLE,))
            result = self.cursor.fetchone()
            if result:
                current_status = result[1]
                new_status = 0 if current_status else 1
                self.cursor.execute("UPDATE todolists SET completed=%s WHERE id=%s", (new_status, taskID_toTOGGLE))
                self.conn.commit()
                self.display_tasks()
            else:
                messagebox.showinfo("오류", "완료 처리할 항목을 선택해주세요.")
        except sqlite3.Error as e:
            messagebox.showerror("DB 오류", f"완료 상태 변경 중 오류 발생:{e}")

    def move_up(self):
        selected = self.task_listbox.curselection()
        if not selected or len(selected) != 1:
            return
        idx = selected[0]
        if idx == 0:
            return
        current_id = self.listbox_task_ids[idx]
        above_id = self.listbox_task_ids[idx - 1]
        self.cursor.execute("SELECT sort_order FROM todolists WHERE id=?", (current_id,))
        order1 = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT sort_order FROM todolists WHERE id=?", (above_id,))
        order2 = self.cursor.fetchone()[0]
        self.cursor.execute("UPDATE todolists SET sort_order=? WHERE id=?", (order2, current_id))
        self.cursor.execute("UPDATE todolists SET sort_order=? WHERE id=?", (order1, above_id))
        self.conn.commit()
        self.display_tasks()
        self.task_listbox.selection_clear(0, tk.END)
        self.task_listbox.selection_set(idx - 1)

    def move_down(self):
        selected = self.task_listbox.curselection()
        if not selected or len(selected) != 1:
            return
        idx = selected[0]
        if idx == len(self.listbox_task_ids) - 1:
            return
        current_id = self.listbox_task_ids[idx]
        below_id = self.listbox_task_ids[idx + 1]
        self.cursor.execute("SELECT sort_order FROM todolists WHERE id=?", (current_id,))
        order1 = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT sort_order FROM todolists WHERE id=?", (below_id,))
        order2 = self.cursor.fetchone()[0]
        self.cursor.execute("UPDATE todolists SET sort_order=? WHERE id=?", (order2, current_id))
        self.cursor.execute("UPDATE todolists SET sort_order=? WHERE id=?", (order1, below_id))
        self.conn.commit()
        self.display_tasks()
        self.task_listbox.selection_clear(0, tk.END)
        self.task_listbox.selection_set(idx + 1)

    def _reorder_sort_orders(self):
        self.cursor.execute("SELECT id FROM todolists ORDER BY sort_order ASC, id ASC")
        rows = self.cursor.fetchall()
        for i, (row_id,) in enumerate(rows):
            self.cursor.execute("UPDATE todolists SET sort_order=? WHERE id=?", (i, row_id))
        self.conn.commit()

    def _ensure_sort_order(self):
        self.cursor.execute("SELECT COUNT(*), SUM(sort_order) FROM todolists")
        count, total = self.cursor.fetchone()
        if count > 1 and (total == 0 or total is None):
            self._reorder_sort_orders()

    def on_closing(self):
        if self.conn:
            self.conn.close()
            print("DB 연결이 종료되었습니다.")
        self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = Todo(root)
    root.mainloop()


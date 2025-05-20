import tkinter as tk
import mysql.connector
from tkinter import messagebox, simpledialog
from datetime import datetime, date
import traceback
import sys

class Todo:

    UNCHECKED = "☐ "
    CHECKED = "☑ "

    def __init__(self, root):
        self.root = root
        root.title("To-do List") #맨 위에 제목("To-do List")
        root.geometry("600x600") #사이즈 약간 넓게 조정

        #db세팅
        self.dbinfo = dict(
            host="34.27.84.32",    # 외부 MySQL 서버 주소로 수정!
            user="todo_user",
            password="mypass123",
            database="todo_db"
        )
        try:
            self.conn = mysql.connector.connect(use_pure=True, **self.dbinfo)
        except Exception as err:
            print("❌ MySQL 연결 중 예외 발생:")
            import traceback
            traceback.print_exc()
            from tkinter import messagebox
            messagebox.showerror("DB 연결 실패", str(err))
            raise
        self.cursor = self.conn.cursor()
        self.cursor.execute("SELECT DATABASE();")
        print(self.cursor.fetchone())

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS todolists (
                id INT AUTO_INCREMENT PRIMARY KEY,
                task VARCHAR(255) NOT NULL,
                completed TINYINT(1) NOT NULL DEFAULT 0,
                sort_order INT NOT NULL DEFAULT 0,
                due_date DATE DEFAULT NULL,
                priority TINYINT NOT NULL DEFAULT 5
            )
        """)

        self.listbox_task_ids = []
        self.deleted_item_stack = []

        self.setup_gui()
        self._ensure_sort_order()
        self.display_tasks()
        root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_gui(self):
        # 입력창
        input_outer_frame = tk.Frame(self.root)
        input_outer_frame.pack(pady = (15, 5))
        
        input_task_frame = tk.Frame(input_outer_frame)
        input_task_frame.pack(pady=2)
        tk.Label(input_task_frame, text="할 일: ").pack(side=tk.LEFT, padx=(0, 5))
        self.task_entry = tk.Entry(input_task_frame, width=40)
        self.task_entry.pack(pady=(15,5))
        self.task_entry.bind("<Return>", self.add_task)
        
        input_priority_frame = tk.Frame(input_outer_frame)
        input_priority_frame.pack(pady=2)
        tk.Label(input_priority_frame, text="우선순위 (0=가장높음, 5=낮음): ").pack(side=tk.LEFT, padx=(0,5))
        self.priority_entry = tk.Entry(input_priority_frame, width=5)
        self.priority_entry.pack(side=tk.LEFT)
        self.priority_entry.insert(0, "5")  # 기본 우선순위
        self.priority_entry.bind("<Return>", self.add_task)


        input_due_date_frame = tk.Frame(input_outer_frame)
        input_due_date_frame.pack(pady=2)
        tk.Label(input_due_date_frame, text="마감기한(YYYY-MM-DD): ").pack(side=tk.LEFT, padx=(0,5))
        self.due_date_entry = tk.Entry(input_due_date_frame, width=15)
        self.due_date_entry.pack(side=tk.LEFT)
        self.due_date_entry.bind("<Return>", self.add_task)

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

        # 버튼 2줄: 순서 이동 + 마감기한 설정
        button_frame2 = tk.Frame(self.root)
        button_frame2.pack(pady=3)
        self.up_button = tk.Button(button_frame2, text="↑ 위로", width=8, command=self.move_up)
        self.up_button.pack(side=tk.LEFT, padx=2)
        self.down_button = tk.Button(button_frame2, text="↓ 아래로", width=8, command=self.move_down)
        self.down_button.pack(side=tk.LEFT, padx=2)
        self.set_due_date_button = tk.Button(button_frame2, text="기한변경", width=8, command=self.set_due_date_for_selected)
        self.set_due_date_button.pack(side=tk.LEFT, padx=2)

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
            self.cursor.execute("SELECT id, task, completed, due_date, priority FROM todolists ORDER BY completed ASC, CASE WHEN due_date IS NULL THEN 1 ELSE 0 END, due_date ASC, id ASC")
            for row in self.cursor.fetchall():
                task_id, task_text, completed_status, due_date, priority = row
                prefix = self.CHECKED if completed_status else self.UNCHECKED
                due_date_str = ""
                if due_date:
                    due_date_str = f"(기한: {due_date.strftime('%Y-%m-%d')})"
                display_text = f"{prefix} {task_text} [우선순위:{priority}] {due_date_str}"

                self.task_listbox.insert(tk.END, display_text)
                self.listbox_task_ids.append(task_id)
                if completed_status:
                    self.task_listbox.itemconfig(tk.END, {'fg': 'gray'})
                elif due_date:
                    today = date.today()
                    if due_date < today:
                        self.task_listbox.itemconfig(tk.END, {'fg': 'darkred'})
                        display_text += "   (기한 지남)"
                    elif due_date == today:
                        self.task_listbox.itemconfig(tk.END, {'fg': 'red'})
                else:
                    self.task_listbox.itemconfig(tk.END, {'fg': 'black'})
        except mysql.connector.Error as e:
            messagebox.showerror("DB 오류", f"할 일 목록을 불러오는 중 오류 발생: {e}")

    def force_refresh(self):
        # 새로고침 시 강제로 DB 연결/커서 다시 열기 (동기화)
        try:
            self.conn.close()
        except:
            pass
        self.conn = mysql.connector.connect(**self.dbinfo)
        self.cursor = self.conn.cursor()
        self.display_tasks()
        self.root.update_idletasks()

    def add_task(self, event=None):
        task = self.task_entry.get()
        due_date_str = self.due_date_entry.get()
        priority_str = self.priority_entry.get()
        try:
            priority = int(priority_str)
            if not (0 <= priority <= 5):
                raise ValueError()
        except ValueError:
            messagebox.showwarning("경고", "우선순위는 0~5 사이의 정수로 입력해주세요.")
            return

        if not task:
            messagebox.showwarning("경고", "할 일을 입력해주세요.")
            return
        
        due_date_obj = None
        if due_date_str.strip():
            try: due_date_obj = datetime.strptime(due_date_str, "%Y-%m-%d").date()
            except ValueError:
                messagebox.showwarning("경고", "마감기한 형식이 잘못되었습니다. (YYYY-MM-DD)")
                return
        try:
            self.cursor.execute("SELECT IFNULL(MAX(sort_order), 0) FROM todolists")
            max_order = self.cursor.fetchone()[0]
            self.cursor.execute("INSERT INTO todolists (task, sort_order, due_date, priority) VALUES (%s, %s, %s, %s)", (task, max_order + 1, due_date_obj, priority))
            self.conn.commit()
            print(f"할 일 추가: {task}, 마감기한: {due_date_obj}")
            self.task_entry.delete(0, tk.END)
            self.due_date_entry.delete(0, tk.END)
            self.display_tasks()
        except mysql.connector.Error as e:
            messagebox.showerror("DB 오류", f"할 일 추가 중 오류 발생: {e}")
        
        
    def set_due_date_for_selected(self):
        selected_indices = self.task_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("경고", "마감기한을 변경할 항목을 선택해주세요.")
            return

        # 첫 번째 선택된 항목의 현재 마감기한을 가져와서 다이얼로그 기본값으로 사용 (선택적)
        first_selected_idx = selected_indices[0]
        task_id_to_get_current_due = self.listbox_task_ids[first_selected_idx]
        initial_due_date_str = ""
        try:
            self.cursor.execute("SELECT due_date FROM todolists WHERE id = %s", (task_id_to_get_current_due,))
            current_due_date_db = self.cursor.fetchone()
            if current_due_date_db and current_due_date_db[0]:
                initial_due_date_str = current_due_date_db[0].strftime('%Y-%m-%d')
        except mysql.connector.Error as e:
            print(f"현재 마감기한 조회 중 오류: {e}") # 오류 발생 시 기본값은 빈 문자열

        # simpledialog를 사용하여 새 마감기한 입력받기
        new_due_date_str = simpledialog.askstring("마감기한 변경",
                                                  "새 마감기한을 입력하세요 (YYYY-MM-DD 형식).\n비우면 마감기한이 제거됩니다.",
                                                  initialvalue=initial_due_date_str)

        if new_due_date_str is None: # 사용자가 '취소'를 누른 경우
            return

        new_due_date_obj = None
        if new_due_date_str.strip(): # 입력값이 있는 경우
            try:
                new_due_date_obj = datetime.strptime(new_due_date_str, "%Y-%m-%d").date()
            except ValueError:
                messagebox.showerror("오류", "잘못된 날짜 형식입니다. (YYYY-MM-DD)")
                return
        # else: 입력값이 비어있으면 new_due_date_obj는 None으로 유지되어 마감기한 제거

        try:
            for index in selected_indices: # 선택된 모든 항목에 대해 마감기한 업데이트
                task_id_to_update = self.listbox_task_ids[index]
                self.cursor.execute("UPDATE todolists SET due_date = %s WHERE id = %s", (new_due_date_obj, task_id_to_update))
            self.conn.commit()
            self.display_tasks() # 변경사항 반영
        except mysql.connector.Error as e:
            messagebox.showerror("DB 오류", f"마감기한 업데이트 중 오류 발생: {e}")

    def delete_task(self):
        selected_indices = self.task_listbox.curselection()
        if selected_indices:
            for index in sorted(selected_indices, reverse=True):
                task_id = self.listbox_task_ids[index]
                try:
                    self.cursor.execute("SELECT id, task, completed, sort_order, due_date FROM todolists WHERE id=%s", (task_id,))
                    deleted_row = self.cursor.fetchone()
                    if deleted_row:
                        self.deleted_item_stack.append(deleted_row)
                        self.cursor.execute("DELETE FROM todolists WHERE id=%s", (task_id,))
                        self.conn.commit()
                except mysql.connector.Error as e:
                    messagebox.showerror("DB 오류", f"할 일 삭제 중 오류 발생: {e}")
            self._reorder_sort_orders()
            self.display_tasks()
        else:
            messagebox.showwarning("경고", "삭제할 항목을 선택해주세요.")

    def undo_delete(self):
        if self.deleted_item_stack:
            last_deleted = self.deleted_item_stack.pop()
            _, task, completed, _, due_date = last_deleted
            try:
                self.cursor.execute("SELECT IFNULL(MAX(sort_order), 0) FROM todolists")
                max_order = self.cursor.fetchone()[0]
                self.cursor.execute("INSERT INTO todolists (task, completed, sort_order, due_date) VALUES (%s, %s, %s, %s)", (task, completed, max_order + 1, due_date))
                self.conn.commit()
                self.display_tasks()
            except mysql.connector.Error as e:
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
            self.cursor.execute("SELECT id, completed FROM todolists WHERE id=%s", (taskID_toTOGGLE,))
            result = self.cursor.fetchone()
            if result:
                current_status = result[1]
                new_status = 0 if current_status else 1
                self.cursor.execute("UPDATE todolists SET completed=%s WHERE id=%s", (new_status, taskID_toTOGGLE))
                self.conn.commit()
                self.display_tasks()
            else:
                messagebox.showinfo("오류", "완료 처리할 항목을 선택해주세요.")
        except mysql.connector.Error as e:
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
        self.cursor.execute("SELECT sort_order FROM todolists WHERE id=%s", (current_id,))
        order1 = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT sort_order FROM todolists WHERE id=%s", (above_id,))
        order2 = self.cursor.fetchone()[0]
        self.cursor.execute("UPDATE todolists SET sort_order=%s WHERE id=%s", (order2, current_id))
        self.cursor.execute("UPDATE todolists SET sort_order=%s WHERE id=%s", (order1, above_id))
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
        self.cursor.execute("SELECT sort_order FROM todolists WHERE id=%s", (current_id,))
        order1 = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT sort_order FROM todolists WHERE id=%s", (below_id,))
        order2 = self.cursor.fetchone()[0]
        self.cursor.execute("UPDATE todolists SET sort_order=%s WHERE id=%s", (order2, current_id))
        self.cursor.execute("UPDATE todolists SET sort_order=%s WHERE id=%s", (order1, below_id))
        self.conn.commit()
        self.display_tasks()
        self.task_listbox.selection_clear(0, tk.END)
        self.task_listbox.selection_set(idx + 1)

    def _reorder_sort_orders(self):
        self.cursor.execute("SELECT id FROM todolists ORDER BY sort_order ASC, id ASC")
        rows = self.cursor.fetchall()
        for i, (row_id,) in enumerate(rows):
            self.cursor.execute("UPDATE todolists SET sort_order=%s WHERE id=%s", (i, row_id))
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
    try:
        app = Todo(root)
        root.mainloop()
    except Exception as e:
        print(f"앱 실행 중 오류 발생 : {e}")
        traceback.print_exc()
        sys.exit(1)
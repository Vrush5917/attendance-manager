async function loadEmployees() {
  try {
    const [empRes, attendanceRes] = await Promise.all([
      fetch('/employees'),
      fetch('/today'),
    ]);
    const empData = await empRes.json();
    const attendanceData = await attendanceRes.json();

    if (!empData.employees) {
      document.getElementById('attendance-list').innerText = "No employees found.";
      return;
    }

    const attendanceMap = {};
    if (attendanceData.attendance) {
      attendanceData.attendance.forEach(e => {
        attendanceMap[e.name] = e.status || 'Absent';
      });
    }

    const container = document.getElementById('attendance-list');
    container.innerHTML = '';

    empData.employees.forEach(emp => {
      const status = attendanceMap[emp] || 'Absent';
      const div = document.createElement('div');
      div.className = 'employee-row';
      div.innerHTML = `
        <label>${emp}</label>
        <select id="status-${emp}">
          <option value="Present" ${status === 'Present' ? 'selected' : ''}>Present</option>
          <option value="Absent" ${status === 'Absent' ? 'selected' : ''}>Absent</option>
        </select>
      `;
      container.appendChild(div);
    });
  } catch (err) {
    document.getElementById('attendance-list').innerText = "Failed to load employees.";
    console.error(err);
  }
}

async function saveAttendance() {
  const empRes = await fetch('/employees');
  const empData = await empRes.json();
  if (!empData.employees) {
    alert("No employees to save attendance for.");
    return;
  }

  const attendance = empData.employees.map(emp => {
    const select = document.getElementById(`status-${emp}`);
    return { name: emp, status: select.value };
  });

  const res = await fetch('/submit_attendance', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ attendance }),
  });
  const result = await res.json();
  alert(result.msg || "Attendance saved.");
}

function downloadPdf() {
  const dateStr = new Date().toISOString().slice(0, 10);
  window.open(`/report?date=${dateStr}`, '_blank');
}

function downloadMonthlyPdf() {
  const monthInput = document.getElementById('month-picker').value;
  if (!monthInput) {
    alert('Please select a month');
    return;
  }
  window.open(`/report/monthly?month=${monthInput}`, '_blank');
}

window.onload = () => {
  loadEmployees();
};

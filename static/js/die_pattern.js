function addRow() {
  const tbody = document.querySelector('#diePatternTable tbody');
  const templateOptions = document.getElementById('partOptionsTemplate').innerHTML;
  
  const newRow = document.createElement('tr');
  newRow.innerHTML = `
    <td>
      <select class="form-select form-select-sm part-select" required>
        ${templateOptions}
      </select>
    </td>
    <td><input type="text" class="form-control form-control-sm pattern_cavity"></td>
    <td><input type="number" step="0.01" class="form-control form-control-sm item_weight"></td>
    <td><input type="text" class="form-control form-control-sm making_pattern_date"></td>
    <td><input type="text" class="form-control form-control-sm complete_pattern_date"></td>
    <td><input type="text" class="form-control form-control-sm send_foundry_pattern_date"></td>
    <td><input type="text" class="form-control form-control-sm casting_date"></td>
    <td><input type="text" class="form-control form-control-sm drawing_date"></td>
    <td><input type="text" class="form-control form-control-sm casting_mc_date"></td>
    <td><input type="text" class="form-control form-control-sm mc_received_date"></td>
    <td><input type="number" step="0.01" class="form-control form-control-sm mc_sample_rate"></td>
    <td><input type="number" step="0.01" class="form-control form-control-sm mc_qty_rate"></td>
    <td><input type="text" class="form-control form-control-sm remark"></td>
    <td class="text-center">
      <select class="form-select form-select-sm status-select bg-warning text-white fw-semibold">
        <option value="PENDING" selected>PENDING</option>
        <option value="COMPLETED">COMPLETED</option>
      </select>
    </td>

    <td class="text-center">
      <button class="btn btn-danger btn-sm" onclick="removeRow(this)">×</button>
    </td>
  `;
  
  tbody.appendChild(newRow);
}

function removeRow(button) {
  const row = button.closest('tr');
  const tbody = row.parentElement;
  
  // Don't remove if it's the last row
  if (tbody.querySelectorAll('tr').length > 1) {
    row.remove();
  } else {
    showAlert('Cannot remove the last row. Add a new row first.', 'warning');
  }
}

function saveAll() {
  const rows = [];
  const tbody = document.querySelector('#diePatternTable tbody');
  const tableRows = tbody.querySelectorAll('tr');
  
  // Validate that all rows have a part selected
  let hasError = false;
  tableRows.forEach(row => {
    const partSelect = row.querySelector('.part-select');
    if (!partSelect.value) {
      partSelect.classList.add('is-invalid');
      hasError = true;
    } else {
      partSelect.classList.remove('is-invalid');
    }
  });
  
  if (hasError) {
    showAlert('Please select a part for all rows', 'danger');
    return;
  }
  
  // Collect all row data
  tableRows.forEach(row => {
    const rowData = {
      part_id: parseInt(row.querySelector('.part-select').value),
      pattern_cavity: row.querySelector('.pattern_cavity').value || null,
      item_weight: row.querySelector('.item_weight').value || null,
      making_pattern_date: row.querySelector('.making_pattern_date').value || null,
      complete_pattern_date: row.querySelector('.complete_pattern_date').value || null,
      send_foundry_pattern_date: row.querySelector('.send_foundry_pattern_date').value || null,
      casting_date: row.querySelector('.casting_date').value || null,
      drawing_date: row.querySelector('.drawing_date').value || null,
      casting_mc_date: row.querySelector('.casting_mc_date').value || null,
      mc_received_date: row.querySelector('.mc_received_date').value || null,
      mc_sample_rate: row.querySelector('.mc_sample_rate').value || null,
      mc_qty_rate: row.querySelector('.mc_qty_rate').value || null,
      remark: row.querySelector('.remark').value || null,
      status: row.querySelector('.status-select')?.value || 'PENDING'

    };
    
    rows.push(rowData);
  });
  
  // Get pump_id from URL
  const pumpId = window.location.pathname.split('/')[2];
  
  // Send to backend
  fetch(`/pumps/${pumpId}/die-pattern`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ rows: rows })
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      showAlert(data.message, 'success');
      // Reload page after 1 second to show updated status
      setTimeout(() => {
        window.location.reload();
      }, 1000);
    } else {
      showAlert(data.message || 'Error saving data', 'danger');
    }
  })
  .catch(error => {
    console.error('Error:', error);
    showAlert('Error saving data. Please try again.', 'danger');
  });
}

function showAlert(message, type) {
  const alertBox = document.getElementById('alertBox');
  alertBox.className = `alert alert-${type}`;
  alertBox.textContent = message;
  alertBox.classList.remove('d-none');
  
  // Auto-hide after 5 seconds
  setTimeout(() => {
    alertBox.classList.add('d-none');
  }, 5000);
}


document.addEventListener('change', function (e) {
  if (e.target.classList.contains('status-select')) {
    e.target.classList.remove('bg-warning', 'bg-success');

    if (e.target.value === 'COMPLETED') {
      e.target.classList.add('bg-success');
    } else {
      e.target.classList.add('bg-warning');
    }
  }
});

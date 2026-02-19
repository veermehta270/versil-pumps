function addRow() {
  const tbody = document.querySelector('#otherItemTable tbody');
  const templateOptions = document.getElementById('partOptionsTemplate').innerHTML;
  
  const newRow = document.createElement('tr');
  newRow.innerHTML = `
    <td>
      <select class="form-select form-select-sm part-select" required>
        ${templateOptions}
      </select>
    </td>
    <td><input type="text" class="form-control form-control-sm material_specification"></td>
    <td><input type="number" step="0.01" class="form-control form-control-sm item_weight"></td>
    <td><input type="text" class="form-control form-control-sm drawing_date"></td>
    <td><input type="text" class="form-control form-control-sm send_party_drawing_date"></td>
    <td><input type="text" class="form-control form-control-sm party_name"></td>
    <td><input type="text" class="form-control form-control-sm party_received_date"></td>
    <td><input type="text" class="form-control form-control-sm inward_date"></td>
    <td><input type="number" step="0.01" class="form-control form-control-sm sample_price"></td>
    <td><input type="number" step="0.01" class="form-control form-control-sm qty_price"></td>
    <td><input type="text" class="form-control form-control-sm qc_date"></td>
    <td>
      <select class="form-select form-select-sm qc_status">
        <option value="">Select</option>
        <option value="OK">OK</option>
        <option value="REJECTED">REJECTED</option>
      </select>
    </td>
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

  document.querySelectorAll("#otherItemTable tbody tr").forEach(tr => {
    const partId = tr.querySelector(".part-select")?.value;
    if (!partId) return;

    rows.push({
      part_id: partId,
      material_specification: tr.querySelector(".material_specification")?.value,
      item_weight: tr.querySelector(".item_weight")?.value,
      drawing_date: tr.querySelector(".drawing_date")?.value,
      send_party_drawing_date: tr.querySelector(".send_party_drawing_date")?.value,
      party_name: tr.querySelector(".party_name")?.value,
      party_received_date: tr.querySelector(".party_received_date")?.value,
      inward_date: tr.querySelector(".inward_date")?.value,
      sample_price: tr.querySelector(".sample_price")?.value,
      qty_price: tr.querySelector(".qty_price")?.value,
      qc_date: tr.querySelector(".qc_date")?.value,
      qc_status: tr.querySelector(".qc_status")?.value,
      remark: tr.querySelector(".remark")?.value,
      status: tr.querySelector(".status-select")?.value
    });
  });

  fetch(window.location.pathname, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Requested-With": "XMLHttpRequest"
    },
    body: JSON.stringify({ rows })
  })
  .then(res => res.json())
  .then(data => {
    const alertBox = document.getElementById("alertBox");

    // Reset classes and add the base 'alert' class
    alertBox.className = 'alert'; // Clear all classes and add base 'alert'
    alertBox.classList.add(data.success ? "alert-success" : "alert-danger");
    alertBox.textContent = data.message;

    // auto-hide after 3 seconds
    setTimeout(() => {
      alertBox.classList.add("d-none");
    }, 3000);
  })
  .catch(err => {
    const alertBox = document.getElementById("alertBox");
    alertBox.className = 'alert alert-danger'; // Add both classes
    alertBox.textContent = "Something went wrong while saving.";
    console.error(err);
  });
}
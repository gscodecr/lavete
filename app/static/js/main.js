class ApiClient {
    constructor() {
        const root = window.APP_ROOT || '/';
        const cleanRoot = root.endsWith('/') ? root.slice(0, -1) : root;
        this.baseUrl = `${cleanRoot}/api/v1`;
        this.token = localStorage.getItem('token');
    }

    async request(endpoint, options = {}) {
        const headers = {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.token}`,
            ...options.headers
        };

        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            ...options,
            headers
        });

        if (response.status === 401) {
            logout();
            return null;
        }

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'API Error');
        }

        if (response.status === 204) {
            return null;
        }

        return response.json();
    }

    async get(endpoint) {
        return await this.request(endpoint);
    }

    async post(endpoint, body) {
        return await this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(body)
        });
    }

    async put(endpoint, body) {
        return await this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(body)
        });
    }

    async delete(endpoint) {
        return await this.request(endpoint, {
            method: 'DELETE'
        });
    }

    // Add put, delete as needed
}

function logout() {
    localStorage.removeItem('token');
    const root = window.APP_ROOT || '/';
    const cleanRoot = root.endsWith('/') ? root.slice(0, -1) : root;
    window.location.href = `${cleanRoot}/login`;
}

async function checkAuth() {
    if (!localStorage.getItem('token')) {
        const root = window.APP_ROOT || '/';
        const cleanRoot = root.endsWith('/') ? root.slice(0, -1) : root;
        window.location.href = `${cleanRoot}/login`;
        return;
    }
    await loadCurrentUser();
}

async function loadCurrentUser() {
    const api = new ApiClient();
    try {
        const user = await api.get('/users/me');
        const userNameParams = document.getElementById('user-name');
        if (userNameParams && user) {
            userNameParams.innerText = user.name || user.email;
        }
    } catch (e) {
        console.error("Failed to load user", e);
        // Optional: logout if token invalid
    }
}

// Table Sorting
function sortTable(n, tableId) {
    var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
    table = document.getElementById(tableId);
    switching = true;
    dir = "asc";
    while (switching) {
        switching = false;
        rows = table.rows;
        for (i = 1; i < (rows.length - 1); i++) {
            shouldSwitch = false;
            x = rows[i].getElementsByTagName("TD")[n];
            y = rows[i + 1].getElementsByTagName("TD")[n];
            if (dir == "asc") {
                if (x.innerHTML.toLowerCase() > y.innerHTML.toLowerCase()) {
                    shouldSwitch = true;
                    break;
                }
            } else if (dir == "desc") {
                if (x.innerHTML.toLowerCase() < y.innerHTML.toLowerCase()) {
                    shouldSwitch = true;
                    break;
                }
            }
        }
        if (shouldSwitch) {
            rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
            switching = true;
            switchcount++;
        } else {
            if (switchcount == 0 && dir == "asc") {
                dir = "desc";
                switching = true;
            }
        }
    }
}

// Table Filtering
function filterTable(tableId, inputVal) {
    var table, tr, td, i, txtValue;
    table = document.getElementById(tableId);
    tr = table.getElementsByTagName("tr");
    inputVal = inputVal.toLowerCase();

    for (i = 1; i < tr.length; i++) {
        // Search all columns
        let found = false;
        for (let j = 0; j < tr[i].cells.length; j++) {
            td = tr[i].getElementsByTagName("td")[j];
            if (td) {
                txtValue = td.textContent || td.innerText;
                if (txtValue.toLowerCase().indexOf(inputVal) > -1) {
                    found = true;
                    break;
                }
            }
        }
        if (found) {
            tr[i].style.display = "";
        } else {
            tr[i].style.display = "none";
        }
    }
}

// Toast Notification Helper
function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    let icon = 'fa-info-circle';
    if (type === 'success') icon = 'fa-check-circle';
    if (type === 'error') icon = 'fa-exclamation-circle';

    toast.innerHTML = `
        <i class="fa-solid ${icon}"></i>
        <span>${message}</span>
    `;

    container.appendChild(toast);

    // Auto remove
    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.5s ease-out forwards';
        setTimeout(() => toast.remove(), 500);
    }, 3000);
}

// Global Confirmation Modal Helper
function showConfirm(title, message, onConfirm) {
    let modal = document.getElementById('confirmation-modal');
    if (!modal) return; // Should be in base.html

    document.getElementById('confirm-title').innerText = title;
    document.getElementById('confirm-message').innerText = message;

    const confirmBtn = document.getElementById('confirm-btn');
    const cancelBtn = document.getElementById('confirm-cancel-btn');

    // Clone button to remove old event listeners
    const newConfirmBtn = confirmBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);

    newConfirmBtn.onclick = () => {
        onConfirm();
        closeConfirmModal();
    };

    const newCancelBtn = cancelBtn.cloneNode(true);
    cancelBtn.parentNode.replaceChild(newCancelBtn, cancelBtn);

    newCancelBtn.onclick = closeConfirmModal;

    modal.style.display = 'flex';
}

function closeConfirmModal() {
    const modal = document.getElementById('confirmation-modal');
    if (modal) modal.style.display = 'none';
}

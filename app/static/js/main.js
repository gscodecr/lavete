class ApiClient {
    constructor() {
        this.baseUrl = '/api/v1';
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

    // Add put, delete as needed
}

function logout() {
    localStorage.removeItem('token');
    window.location.href = '/login';
}

async function checkAuth() {
    if (!localStorage.getItem('token')) {
        window.location.href = '/login';
    }
    // Optionally verify token validity with a /me endpoint
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

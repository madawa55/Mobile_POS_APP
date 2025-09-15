// Global JavaScript for POS System

// Utility functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function formatDate(date) {
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }).format(new Date(date));
}

// Toast notification system
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container') || createToastContainer();

    const toast = document.createElement('div');
    toast.className = `toast show align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;

    toastContainer.appendChild(toast);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        toast.remove();
    }, 5000);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed top-0 end-0 p-3';
    container.style.zIndex = '1055';
    document.body.appendChild(container);
    return container;
}

// Loading indicator
function showLoading() {
    const loading = document.createElement('div');
    loading.id = 'loading-overlay';
    loading.innerHTML = `
        <div class="loading-spinner">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <div class="mt-2">Loading...</div>
        </div>
    `;
    loading.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9999;
        color: white;
    `;
    document.body.appendChild(loading);
}

function hideLoading() {
    const loading = document.getElementById('loading-overlay');
    if (loading) {
        loading.remove();
    }
}

// API helper functions
async function apiCall(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };

    const config = { ...defaultOptions, ...options };

    try {
        const response = await fetch(url, config);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.message || 'API call failed');
        }

        return data;
    } catch (error) {
        console.error('API Error:', error);
        showToast(error.message, 'danger');
        throw error;
    }
}

// Barcode scanning utility
class BarcodeScanner {
    constructor(inputElement, callback) {
        this.input = inputElement;
        this.callback = callback;
        this.buffer = '';
        this.bufferTimeout = null;

        this.setupEventListeners();
    }

    setupEventListeners() {
        this.input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                if (this.buffer.length > 0) {
                    this.callback(this.buffer);
                    this.buffer = '';
                }
                e.preventDefault();
            } else {
                this.buffer += e.key;

                // Clear buffer after 500ms of inactivity
                clearTimeout(this.bufferTimeout);
                this.bufferTimeout = setTimeout(() => {
                    this.buffer = '';
                }, 500);
            }
        });
    }
}

// Inventory alerts
function checkLowStockAlerts() {
    // This would be called periodically to check for low stock items
    const lowStockThreshold = 10;

    // In a real implementation, this would fetch data from the server
    fetch('/api/low-stock-items')
        .then(response => response.json())
        .then(items => {
            if (items.length > 0) {
                showToast(`${items.length} items are running low on stock!`, 'warning');
            }
        })
        .catch(error => {
            console.error('Error checking stock levels:', error);
        });
}

// Print functionality
function printElement(elementId, title = 'Print') {
    const element = document.getElementById(elementId);
    if (!element) return;

    const printWindow = window.open('', '_blank', 'width=300,height=500');
    printWindow.document.write(`
        <!DOCTYPE html>
        <html>
            <head>
                <title>${title}</title>
                <style>
                    body {
                        font-family: 'Courier New', monospace;
                        font-size: 12px;
                        line-height: 1.4;
                        margin: 0;
                        padding: 10px;
                    }
                    @media print {
                        body { margin: 0; padding: 0; }
                        .no-print { display: none !important; }
                    }
                    table { width: 100%; border-collapse: collapse; }
                    th, td { text-align: left; padding: 2px 0; }
                    .text-center { text-align: center; }
                    .text-right { text-align: right; }
                    hr { border: none; border-top: 1px dashed #000; margin: 10px 0; }
                </style>
            </head>
            <body>
                ${element.innerHTML}
                <script>
                    window.onload = function() {
                        window.print();
                        window.onafterprint = function() {
                            window.close();
                        };
                    };
                </script>
            </body>
        </html>
    `);
    printWindow.document.close();
}

// Data export functionality
function exportToCSV(data, filename = 'export.csv') {
    const csv = Papa.unparse(data);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');

    if (link.download !== undefined) {
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

// Local storage helpers
function saveToStorage(key, data) {
    try {
        localStorage.setItem(key, JSON.stringify(data));
    } catch (error) {
        console.error('Error saving to storage:', error);
    }
}

function getFromStorage(key, defaultValue = null) {
    try {
        const data = localStorage.getItem(key);
        return data ? JSON.parse(data) : defaultValue;
    } catch (error) {
        console.error('Error reading from storage:', error);
        return defaultValue;
    }
}

// Keyboard shortcuts
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Only trigger shortcuts when not typing in form fields
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return;
        }

        // Ctrl/Cmd + specific keys
        if (e.ctrlKey || e.metaKey) {
            switch (e.key) {
                case 'p': // Print
                    e.preventDefault();
                    if (typeof printReceipt === 'function') {
                        printReceipt();
                    }
                    break;
                case 'n': // New transaction
                    e.preventDefault();
                    if (typeof clearCart === 'function') {
                        clearCart();
                    }
                    break;
                case 'f': // Focus search
                    e.preventDefault();
                    const searchInput = document.getElementById('searchInput') ||
                                      document.getElementById('barcodeInput');
                    if (searchInput) {
                        searchInput.focus();
                    }
                    break;
            }
        }

        // Function keys
        switch (e.key) {
            case 'F1': // Help
                e.preventDefault();
                showKeyboardShortcuts();
                break;
            case 'F2': // Quick add product
                e.preventDefault();
                if (window.location.pathname.includes('pos')) {
                    document.getElementById('barcodeInput')?.focus();
                }
                break;
            case 'F9': // Cash payment
                e.preventDefault();
                if (typeof processPayment === 'function') {
                    processPayment('cash');
                }
                break;
            case 'F10': // Card payment
                e.preventDefault();
                if (typeof processPayment === 'function') {
                    processPayment('card');
                }
                break;
        }
    });
}

function showKeyboardShortcuts() {
    const shortcuts = [
        { key: 'Ctrl/Cmd + P', action: 'Print Receipt' },
        { key: 'Ctrl/Cmd + N', action: 'New Transaction' },
        { key: 'Ctrl/Cmd + F', action: 'Focus Search' },
        { key: 'F1', action: 'Show Help' },
        { key: 'F2', action: 'Focus Barcode Scanner' },
        { key: 'F9', action: 'Cash Payment' },
        { key: 'F10', action: 'Card Payment' }
    ];

    const shortcutsHtml = shortcuts.map(s =>
        `<tr><td><kbd>${s.key}</kbd></td><td>${s.action}</td></tr>`
    ).join('');

    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Keyboard Shortcuts</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>Shortcut</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${shortcutsHtml}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();

    modal.addEventListener('hidden.bs.modal', () => {
        modal.remove();
    });
}

// Auto-save functionality for forms
function setupAutoSave(formId, storageKey) {
    const form = document.getElementById(formId);
    if (!form) return;

    // Load saved data
    const savedData = getFromStorage(storageKey);
    if (savedData) {
        Object.keys(savedData).forEach(key => {
            const element = form.querySelector(`[name="${key}"]`);
            if (element) {
                element.value = savedData[key];
            }
        });
    }

    // Auto-save on input
    form.addEventListener('input', debounce(() => {
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        saveToStorage(storageKey, data);
    }, 1000));

    // Clear saved data on successful submission
    form.addEventListener('submit', () => {
        localStorage.removeItem(storageKey);
    });
}

// Debounce utility
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Initialize global functionality
document.addEventListener('DOMContentLoaded', function() {
    // Setup keyboard shortcuts
    setupKeyboardShortcuts();

    // Auto-focus first input field
    const firstInput = document.querySelector('input[type="text"]:not([readonly]), input[type="email"]:not([readonly])');
    if (firstInput) {
        firstInput.focus();
    }

    // Setup tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Check for low stock alerts periodically (every 5 minutes)
    if (window.location.pathname.includes('dashboard')) {
        checkLowStockAlerts();
        setInterval(checkLowStockAlerts, 5 * 60 * 1000);
    }

    // Setup auto-save for forms
    if (document.getElementById('productForm')) {
        setupAutoSave('productForm', 'product_form_draft');
    }

    // Show version info in console
    console.log('POS System v1.0.0 - Multi-Business Solution');
    console.log('Press F1 for keyboard shortcuts');
});

// Export functions for global use
window.POS = {
    formatCurrency,
    formatDate,
    showToast,
    showLoading,
    hideLoading,
    apiCall,
    BarcodeScanner,
    printElement,
    exportToCSV,
    saveToStorage,
    getFromStorage
};
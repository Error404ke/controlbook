const productForm = document.getElementById('product-form');
const productTableBody = document.getElementById('product-table-body');
const refreshButton = document.getElementById('refresh-button');
const clearHistoryButton = document.getElementById('clear-history-button');
const messageBox = document.getElementById('message');
const totalSalesCount = document.getElementById('sales-count');
const totalSalesTotal = document.getElementById('sales-total');

const currencyFormatter = new Intl.NumberFormat('en-KE', {
    style: 'currency',
    currency: 'KES',
    minimumFractionDigits: 2,
});

const showMessage = (text, type = 'info') => {
    messageBox.textContent = text;
    messageBox.className = `message ${type}`;
    setTimeout(() => {
        messageBox.textContent = '';
        messageBox.className = 'message';
    }, 4000);
};

const formatKES = (value) => {
    if (typeof value !== 'number' || Number.isNaN(value)) {
        return currencyFormatter.format(0);
    }
    return currencyFormatter.format(value);
};

const buildRow = (product) => {
    const row = document.createElement('tr');

    row.innerHTML = `
        <td>${product.name}</td>
        <td>${product.category}</td>
        <td>${product.quantity}</td>
        <td>${formatKES(Number(product.price))}</td>
        <td class="actions">
            <button class="sell-button" data-id="${product._id}">Sell</button>
            <button class="restock-button" data-id="${product._id}">Restock</button>
        </td>
    `;

    const sellButton = row.querySelector('.sell-button');
    const restockButton = row.querySelector('.restock-button');

    sellButton.addEventListener('click', async () => {
        const quantity = Number(prompt('Enter quantity to sell:', '1'));
        if (!quantity || quantity <= 0) {
            showMessage('Please enter a valid sell quantity.', 'error');
            return;
        }
        await postAction(`/sell/${product._id}`, { quantity });
    });

    restockButton.addEventListener('click', async () => {
        const quantity = Number(prompt('Enter quantity to restock:', '1'));
        if (!quantity || quantity <= 0) {
            showMessage('Please enter a valid restock quantity.', 'error');
            return;
        }
        await postAction(`/restock/${product._id}`, { quantity });
    });

    return row;
};

const loadProducts = async () => {
    try {
        const response = await fetch('/products');
        const products = await response.json();

        productTableBody.innerHTML = '';
        if (!Array.isArray(products) || products.length === 0) {
            productTableBody.innerHTML = '<tr><td colspan="5">No products yet.</td></tr>';
            return;
        }

        products.forEach((product) => {
            productTableBody.appendChild(buildRow(product));
        });
    } catch (error) {
        showMessage('Failed to load products.', 'error');
        console.error(error);
    }
};

const loadSalesSummary = async () => {
    try {
        const response = await fetch('/sales/total');
        const summary = await response.json();

        totalSalesCount.textContent = summary.totalItems ?? 0;
        totalSalesTotal.textContent = formatKES(Number(summary.totalRevenue ?? 0));
    } catch (error) {
        showMessage('Failed to load sales summary.', 'error');
        console.error(error);
    }
};

const postAction = async (path, payload) => {
    try {
        const response = await fetch(path, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        const result = await response.json();
        if (!response.ok) {
            showMessage(result.message || 'Action failed.', 'error');
            return;
        }

        showMessage(result.message || 'Action completed.', 'success');
        loadProducts();
        loadSalesSummary();
    } catch (error) {
        showMessage('Request failed.', 'error');
        console.error(error);
    }
};

productForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    const formData = new FormData(productForm);
    const payload = {
        name: formData.get('name').trim(),
        category: formData.get('category').trim(),
        quantity: Number(formData.get('quantity')),
        price: Number(formData.get('price')),
    };

    if (!payload.name || !payload.category || payload.quantity < 0 || payload.price < 0) {
        showMessage('Please complete all fields correctly.', 'error');
        return;
    }

    await postAction('/products', payload);
    productForm.reset();
});

clearHistoryButton?.addEventListener('click', async () => {
    const confirmClear = confirm('Clear sales history? This cannot be undone.');
    if (!confirmClear) {
        return;
    }

    const pin = prompt('Enter PIN to clear sales history:');
    if (!pin) {
        showMessage('History clear canceled.', 'error');
        return;
    }

    try {
        const response = await fetch('/history/clear', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pin })
        });

        const result = await response.json();
        if (!response.ok) {
            showMessage(result.message || 'Failed to clear history.', 'error');
            return;
        }

        showMessage(result.message || 'History cleared.', 'success');
        loadSalesSummary();
    } catch (error) {
        showMessage('Failed to clear history.', 'error');
        console.error(error);
    }
});

refreshButton.addEventListener('click', () => {
    loadProducts();
    loadSalesSummary();
});
window.addEventListener('load', () => {
    loadProducts();
    loadSalesSummary();
});

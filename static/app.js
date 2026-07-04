const productForm = document.getElementById('product-form');
const productTableBody = document.getElementById('product-table-body');
const refreshButton = document.getElementById('refresh-button');
const downloadSalesButton = document.getElementById('download-sales-button');
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
            <button class="sell-button" data-id="${product.id}">Sell</button>
            <button class="restock-button" data-id="${product.id}">Restock</button>
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
        await postAction(`/sell/${product.id}`, { quantity });
    });

    restockButton.addEventListener('click', async () => {
        const quantity = Number(prompt('Enter quantity to restock:', '1'));
        if (!quantity || quantity <= 0) {
            showMessage('Please enter a valid restock quantity.', 'error');
            return;
        }
        await postAction(`/restock/${product.id}`, { quantity });
    });

    return row;
};

const loadProducts = async () => {
    try {
        const response = await fetch('/products');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
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

downloadSalesButton?.addEventListener('click', () => {
    window.location.href = '/sales/download';
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
    initBackgroundGraph();
});

const initBackgroundGraph = () => {
    const canvas = document.getElementById('background-canvas');
    if (!canvas) {
        return;
    }

    const ctx = canvas.getContext('2d');
    const points = [];
    const POINT_COUNT = 36;
    const LINE_DISTANCE = 190;
    const SPEED = 0.32;
    const CURSOR_RANGE = 250;
    
    let mouseX = canvas.width / 2;
    let mouseY = canvas.height / 2;

    const resize = () => {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    };

    const randomBetween = (min, max) => Math.random() * (max - min) + min;

    const createPoints = () => {
        points.length = 0;
        for (let i = 0; i < POINT_COUNT; i += 1) {
            points.push({
                x: randomBetween(0, canvas.width),
                y: randomBetween(0, canvas.height),
                vx: randomBetween(-SPEED, SPEED),
                vy: randomBetween(-SPEED, SPEED),
                radius: randomBetween(1.2, 2.8),
            });
        }
    };

    document.addEventListener('mousemove', (e) => {
        mouseX = e.clientX;
        mouseY = e.clientY;
    });

    document.addEventListener('mouseleave', () => {
        mouseX = canvas.width / 2;
        mouseY = canvas.height / 2;
    });

    const animate = () => {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        points.forEach((point, index) => {
            const dx = mouseX - point.x;
            const dy = mouseY - point.y;
            const distToMouse = Math.sqrt(dx * dx + dy * dy);

            if (distToMouse < CURSOR_RANGE) {
                const force = (CURSOR_RANGE - distToMouse) / CURSOR_RANGE * 0.15;
                point.vx += (dx / distToMouse) * force;
                point.vy += (dy / distToMouse) * force;
            }

            point.vx *= 0.98;
            point.vy *= 0.98;

            point.x += point.vx;
            point.y += point.vy;

            if (point.x <= 0 || point.x >= canvas.width) {
                point.vx *= -1;
            }
            if (point.y <= 0 || point.y >= canvas.height) {
                point.vy *= -1;
            }

            ctx.beginPath();
            ctx.arc(point.x, point.y, point.radius * 1.5, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(122, 213, 111, 1)';
            ctx.shadowColor = 'rgba(122, 213, 111, 0.7)';
            ctx.shadowBlur = 10;
            ctx.fill();
            ctx.shadowBlur = 0;

            for (let j = index + 1; j < points.length; j += 1) {
                const other = points[j];
                const dx = point.x - other.x;
                const dy = point.y - other.y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < LINE_DISTANCE) {
                    const alpha = 1 - dist / LINE_DISTANCE;
                    ctx.strokeStyle = `rgba(122, 213, 111, ${alpha * 0.65})`;
                    ctx.lineWidth = 1.4;
                    ctx.beginPath();
                    ctx.moveTo(point.x, point.y);
                    ctx.lineTo(other.x, other.y);
                    ctx.stroke();
                }
            }
        });

        requestAnimationFrame(animate);
    };

    window.addEventListener('resize', () => {
        resize();
        createPoints();
    });

    resize();
    createPoints();
    animate();
};

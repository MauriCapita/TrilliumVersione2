// Variabili globali
let allCustomers = [];
let allOrders = [];
let detailsCache = {}; // Cache per i dettagli completi
let searchTimeout = null; // Timeout per debounce della ricerca

// Gestione tab
function showTab(tabName) {
    // Nascondi tutte le tab
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Rimuovi active da tutti i bottoni
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Mostra la tab selezionata
    document.getElementById(`${tabName}-tab`).classList.add('active');
    event.target.classList.add('active');
    
    // Carica i dati se necessario
    if (tabName === 'orders' && allOrders.length === 0) {
        loadOrders();
    } else if (tabName === 'customers' && allCustomers.length === 0) {
        loadCustomers();
    }
}

// Carica ordini
async function loadOrders() {
    const container = document.getElementById('orders-container');
    const loading = document.getElementById('orders-loading');
    
    container.innerHTML = '';
    loading.style.display = 'block';
    detailsCache = {}; // Pulisci la cache
    
    try {
        const response = await fetch('/api/orders');
        const data = await response.json();
        
        loading.style.display = 'none';
        
        if (data.success && data.orders) {
            allOrders = data.orders;
            displayOrders(data.orders);
        } else {
            container.innerHTML = `<div class="empty-state">Errore nel caricamento: ${data.error || 'Errore sconosciuto'}</div>`;
        }
    } catch (error) {
        loading.style.display = 'none';
        container.innerHTML = `<div class="empty-state">Errore di connessione: ${error.message}</div>`;
    }
}

// Cerca un singolo ordine per ID
async function searchOrder(orderId) {
    const container = document.getElementById('orders-container');
    const loading = document.getElementById('orders-loading');
    const empty = document.getElementById('orders-empty');
    
    // Se la ricerca è vuota, mostra tutti gli ordini
    if (!orderId.trim()) {
        if (allOrders.length > 0) {
            displayOrders(allOrders);
            empty.style.display = 'none';
        } else {
            loadOrders();
        }
        return;
    }
    
    // Se la ricerca non è un numero valido, non fare nulla
    if (!/^\d+$/.test(orderId.trim())) {
        return;
    }
    
    const searchId = parseInt(orderId.trim());
    
    // Prima cerca tra gli ordini già caricati
    if (allOrders.length > 0) {
        const foundOrder = allOrders.find(order => {
            const orderIdNum = parseInt(order.id || order.id_cart || 0);
            return orderIdNum === searchId;
        });
        
        if (foundOrder) {
            // Ordine trovato tra quelli già caricati
            displayOrders([foundOrder]);
            empty.style.display = 'none';
            
            // Scrolla e evidenzia l'ordine trovato
            setTimeout(() => {
                const cards = container.querySelectorAll('.card');
                if (cards.length > 0) {
                    const card = cards[0];
                    // Scrolla al container prima, poi alla card
                    container.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    setTimeout(() => {
                        card.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        card.classList.add('highlight-search');
                        setTimeout(() => {
                            card.classList.remove('highlight-search');
                        }, 2000);
                    }, 200);
                }
            }, 100);
            return;
        }
    }
    
    // Se non trovato tra quelli caricati, cerca via API
    loading.style.display = 'block';
    container.innerHTML = '';
    empty.style.display = 'none';
    detailsCache = {}; // Pulisci la cache
    
    try {
        const response = await fetch(`/api/orders/search?id=${encodeURIComponent(orderId.trim())}`);
        const data = await response.json();
        
        loading.style.display = 'none';
        
        if (data.success && data.order) {
            // Mostra il singolo ordine trovato
            displayOrders([data.order]);
            empty.style.display = 'none';
            
            // Scrolla e evidenzia l'ordine trovato
            setTimeout(() => {
                const cards = container.querySelectorAll('.card');
                if (cards.length > 0) {
                    const card = cards[0];
                    // Scrolla al container prima, poi alla card
                    container.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    setTimeout(() => {
                        card.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        card.classList.add('highlight-search');
                        setTimeout(() => {
                            card.classList.remove('highlight-search');
                        }, 2000);
                    }, 200);
                }
            }, 100);
        } else {
            container.innerHTML = '';
            empty.style.display = 'block';
            empty.textContent = data.error || 'Ordine non trovato';
        }
    } catch (error) {
        loading.style.display = 'none';
        container.innerHTML = `<div class="empty-state">Errore di connessione: ${error.message}</div>`;
    }
}

// Mostra ordini
function displayOrders(orders) {
    const container = document.getElementById('orders-container');
    
    if (orders.length === 0) {
        container.innerHTML = '<div class="empty-state">Nessun ordine trovato</div>';
        return;
    }
    
    container.innerHTML = orders.map((order, index) => {
        const orderId = order.id || order.id_cart || 'N/A';
        const totalPaid = order.total_paid || order.total_paid_real || '0.00';
        const date = order.date_add || order.date_upd || 'N/A';
        const status = getOrderStatus(order.current_state);
        const customerName = order.id_customer ? `Cliente #${order.id_customer}` : 'N/A';
        const detailsId = `order-details-${index}`;
        const cacheKey = `order-${index}`;
        
        // Salva i dati nella cache
        detailsCache[cacheKey] = order;
        
        // Funzione helper per formattare valori
        const formatValue = (value) => {
            if (value === null || value === undefined || value === '') return 'N/A';
            if (typeof value === 'boolean') return value ? 'Sì' : 'No';
            if (typeof value === 'object') return JSON.stringify(value);
            return value;
        };
        
        // Raccogli tutti i campi disponibili
        const allFields = Object.keys(order).sort();
        const mainFields = ['id', 'reference', 'id_customer', 'current_state', 'total_paid', 'total_paid_real', 
                           'total_products', 'total_products_wt', 'total_shipping', 'total_shipping_tax_incl',
                           'date_add', 'date_upd', 'payment', 'module', 'id_currency', 'id_lang', 
                           'id_carrier', 'id_address_delivery', 'id_address_invoice', 'invoice_number', 
                           'invoice_date', 'delivery_number', 'delivery_date', 'shipping_number', 'tracking_number',
                           'gift', 'gift_message', 'conversion_rate', 'valid', 'note'];
        
        const otherFields = allFields.filter(f => !mainFields.includes(f));
        const shippingNumber = order.shipping_number || order.tracking_number || '';
        const shippingSectionId = `shipping-${index}`;
        
        return `
            <div class="card">
                <div class="card-header">
                    <div class="card-title">Ordine #${orderId}</div>
                    <span class="status ${status.class}">${status.text}</span>
                </div>
                
                <!-- Informazioni Spedizione ShippyPro -->
                ${shippingNumber ? `
                <div class="shipping-section">
                    <div class="shipping-header">
                        <h4>📦 Informazioni Spedizione ShippyPro</h4>
                        <div class="shipping-number">Tracking: <strong class="shipping-number-clickable" onclick="loadShippingInfo('${shippingNumber}', '${shippingSectionId}')" title="Clicca per vedere i dettagli">${shippingNumber}</strong></div>
                    </div>
                    <button class="load-shipping-btn" onclick="loadShippingInfo('${shippingNumber}', '${shippingSectionId}')">
                        🔍 Carica Dettagli Tracking Completi
                    </button>
                    <div id="${shippingSectionId}" class="shipping-info" style="display: none;">
                        <div class="shipping-loading">Caricamento informazioni...</div>
                    </div>
                </div>
                ` : ''}
                
                <!-- Campi principali -->
                <div class="details-section">
                    <div class="card-grid-2">
                        <div class="card-info">
                            <div class="card-label">ID Ordine</div>
                            <div class="card-value">${formatValue(order.id)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Riferimento</div>
                            <div class="card-value">${formatValue(order.reference)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">ID Cliente</div>
                            <div class="card-value">${formatValue(order.id_customer)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Stato</div>
                            <div class="card-value">${status.text} (${formatValue(order.current_state)})</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Totale Pagato</div>
                            <div class="card-value">€ ${parseFloat(totalPaid).toFixed(2)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Totale Prodotti</div>
                            <div class="card-value">€ ${parseFloat(order.total_products || 0).toFixed(2)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Totale Prodotti (con IVA)</div>
                            <div class="card-value">€ ${parseFloat(order.total_products_wt || 0).toFixed(2)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Totale Spedizione</div>
                            <div class="card-value">€ ${parseFloat(order.total_shipping || 0).toFixed(2)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Totale Spedizione (con IVA)</div>
                            <div class="card-value">€ ${parseFloat(order.total_shipping_tax_incl || 0).toFixed(2)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Metodo Pagamento</div>
                            <div class="card-value">${formatValue(order.payment)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Modulo Pagamento</div>
                            <div class="card-value">${formatValue(order.module)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">ID Valuta</div>
                            <div class="card-value">${formatValue(order.id_currency)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">ID Lingua</div>
                            <div class="card-value">${formatValue(order.id_lang)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">ID Corriere</div>
                            <div class="card-value">${formatValue(order.id_carrier)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">ID Indirizzo Consegna</div>
                            <div class="card-value">${formatValue(order.id_address_delivery)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">ID Indirizzo Fatturazione</div>
                            <div class="card-value">${formatValue(order.id_address_invoice)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Numero Fattura</div>
                            <div class="card-value">${formatValue(order.invoice_number)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Data Fattura</div>
                            <div class="card-value">${formatValue(order.invoice_date ? formatDate(order.invoice_date) : 'N/A')}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Numero Consegna</div>
                            <div class="card-value">${formatValue(order.delivery_number)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Data Consegna</div>
                            <div class="card-value">${formatValue(order.delivery_date ? formatDate(order.delivery_date) : 'N/A')}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Numero Spedizione (ShippyPro)</div>
                            ${shippingNumber ? `
                            <div class="card-value">
                                <span class="shipping-number-clickable" onclick="loadShippingInfo('${shippingNumber}', '${shippingSectionId}')" title="Clicca per vedere i dettagli del tracking">
                                    ${shippingNumber}
                                </span>
                            </div>
                            ` : '<div class="card-value">N/A</div>'}
                        </div>
                        <div class="card-info">
                            <div class="card-label">Regalo</div>
                            <div class="card-value">${formatValue(order.gift)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Messaggio Regalo</div>
                            <div class="card-value">${formatValue(order.gift_message)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Tasso di Conversione</div>
                            <div class="card-value">${formatValue(order.conversion_rate)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Valido</div>
                            <div class="card-value">${formatValue(order.valid)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Note</div>
                            <div class="card-value">${formatValue(order.note)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Data Creazione</div>
                            <div class="card-value">${formatDate(date)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Data Aggiornamento</div>
                            <div class="card-value">${formatValue(order.date_upd ? formatDate(order.date_upd) : 'N/A')}</div>
                        </div>
                    </div>
                    
                    ${otherFields.length > 0 ? `
                    <div class="expandable-section">
                        <button class="expand-btn" onclick="toggleDetails('${detailsId}')">
                            <span class="expand-icon">▼</span> Altri Campi (${otherFields.length})
                        </button>
                        <div id="${detailsId}" class="details-expanded" style="display: none;">
                            ${otherFields.map(field => `
                                <div class="card-info">
                                    <div class="card-label">${field}</div>
                                    <div class="card-value">${formatValue(order[field])}</div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    ` : ''}
                    
                    <button class="details-btn" onclick="showFullDetailsFromCache('${cacheKey}')">
                        📋 Mostra Dati JSON Completi
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

// Carica clienti
async function loadCustomers() {
    const container = document.getElementById('customers-container');
    const loading = document.getElementById('customers-loading');
    const empty = document.getElementById('customers-empty');
    
    container.innerHTML = '';
    loading.style.display = 'block';
    empty.style.display = 'none';
    detailsCache = {}; // Pulisci la cache
    
    try {
        const response = await fetch('/api/customers');
        const data = await response.json();
        
        loading.style.display = 'none';
        
        if (data.success && data.customers) {
            allCustomers = data.customers;
            displayCustomers(data.customers);
        } else {
            container.innerHTML = `<div class="empty-state">Errore nel caricamento: ${data.error || 'Errore sconosciuto'}</div>`;
        }
    } catch (error) {
        loading.style.display = 'none';
        container.innerHTML = `<div class="empty-state">Errore di connessione: ${error.message}</div>`;
    }
}

// Filtra clienti
async function filterCustomers(query) {
    const container = document.getElementById('customers-container');
    const loading = document.getElementById('customers-loading');
    const empty = document.getElementById('customers-empty');
    
    // Se la query è vuota, mostra tutti i clienti
    if (!query.trim()) {
        if (allCustomers.length > 0) {
            displayCustomers(allCustomers);
            empty.style.display = 'none';
        } else {
            loadCustomers();
        }
        return;
    }
    
    // Se la query è troppo corta, non fare nulla
    if (query.length < 2) {
        return;
    }
    
    loading.style.display = 'block';
    container.innerHTML = '';
    empty.style.display = 'none';
    detailsCache = {}; // Pulisci la cache
    
    try {
        const response = await fetch(`/api/customers/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        
        loading.style.display = 'none';
        
        if (data.success && data.customers) {
            if (data.customers.length > 0) {
                displayCustomers(data.customers);
                empty.style.display = 'none';
            } else {
                container.innerHTML = '';
                empty.style.display = 'block';
            }
        } else {
            container.innerHTML = `<div class="empty-state">Errore nella ricerca: ${data.error || 'Errore sconosciuto'}</div>`;
        }
    } catch (error) {
        loading.style.display = 'none';
        container.innerHTML = `<div class="empty-state">Errore di connessione: ${error.message}</div>`;
    }
}

// Mostra clienti
function displayCustomers(customers) {
    const container = document.getElementById('customers-container');
    
    if (customers.length === 0) {
        container.innerHTML = '<div class="empty-state">Nessun cliente trovato</div>';
        return;
    }
    
    container.innerHTML = customers.map((customer, index) => {
        const id = customer.id || 'N/A';
        const firstName = customer.firstname || 'N/A';
        const lastName = customer.lastname || 'N/A';
        const email = customer.email || 'N/A';
        const company = customer.company || '';
        const phone = customer.phone || customer.phone_mobile || 'N/A';
        const date = customer.date_add || 'N/A';
        const detailsId = `customer-details-${index}`;
        const cacheKey = `customer-${index}`;
        
        // Salva i dati nella cache
        detailsCache[cacheKey] = customer;
        
        // Funzione helper per formattare valori
        const formatValue = (value) => {
            if (value === null || value === undefined || value === '') return 'N/A';
            if (typeof value === 'boolean') return value ? 'Sì' : 'No';
            if (typeof value === 'object') return JSON.stringify(value);
            return value;
        };
        
        // Raccogli tutti i campi disponibili
        const allFields = Object.keys(customer).sort();
        const mainFields = ['id', 'id_default_group', 'id_lang', 'newsletter', 'optin', 'active', 
                           'secure_key', 'note', 'is_guest', 'id_shop', 'id_shop_group', 
                           'date_add', 'date_upd', 'last_passwd_gen', 'last_connection_date',
                           'firstname', 'lastname', 'email', 'passwd', 'birthday', 'newsletter_date_add',
                           'ip_registration_newsletter', 'company', 'siret', 'ape', 'website', 
                           'phone', 'phone_mobile', 'deleted', 'id_gender', 'max_payment_days'];
        
        const otherFields = allFields.filter(f => !mainFields.includes(f));
        
        return `
            <div class="card">
                <div class="card-header">
                    <div class="card-title">${firstName} ${lastName}</div>
                    <div class="card-badge">ID: ${id}</div>
                </div>
                
                <!-- Campi principali -->
                <div class="details-section">
                    <div class="card-grid-2">
                        <div class="card-info">
                            <div class="card-label">ID Cliente</div>
                            <div class="card-value">${formatValue(customer.id)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Nome</div>
                            <div class="card-value">${formatValue(customer.firstname)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Cognome</div>
                            <div class="card-value">${formatValue(customer.lastname)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Email</div>
                            <div class="card-value">
                                <a href="mailto:${email}" class="card-email">${formatValue(customer.email)}</a>
                            </div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Azienda</div>
                            <div class="card-value">${formatValue(customer.company)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">SIRET</div>
                            <div class="card-value">${formatValue(customer.siret)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">APE</div>
                            <div class="card-value">${formatValue(customer.ape)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Sito Web</div>
                            <div class="card-value">${formatValue(customer.website)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Telefono</div>
                            <div class="card-value">${formatValue(customer.phone)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Cellulare</div>
                            <div class="card-value">${formatValue(customer.phone_mobile)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Data di Nascita</div>
                            <div class="card-value">${formatValue(customer.birthday)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Genere</div>
                            <div class="card-value">${formatValue(customer.id_gender)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">ID Gruppo Default</div>
                            <div class="card-value">${formatValue(customer.id_default_group)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">ID Lingua</div>
                            <div class="card-value">${formatValue(customer.id_lang)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Newsletter</div>
                            <div class="card-value">${formatValue(customer.newsletter)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Opt-in</div>
                            <div class="card-value">${formatValue(customer.optin)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Attivo</div>
                            <div class="card-value">${formatValue(customer.active)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Ospite</div>
                            <div class="card-value">${formatValue(customer.is_guest)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Eliminato</div>
                            <div class="card-value">${formatValue(customer.deleted)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">ID Shop</div>
                            <div class="card-value">${formatValue(customer.id_shop)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">ID Shop Group</div>
                            <div class="card-value">${formatValue(customer.id_shop_group)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Chiave Sicura</div>
                            <div class="card-value">${formatValue(customer.secure_key)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Note</div>
                            <div class="card-value">${formatValue(customer.note)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Data Registrazione</div>
                            <div class="card-value">${formatDate(date)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Data Aggiornamento</div>
                            <div class="card-value">${formatValue(customer.date_upd ? formatDate(customer.date_upd) : 'N/A')}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Ultima Generazione Password</div>
                            <div class="card-value">${formatValue(customer.last_passwd_gen ? formatDate(customer.last_passwd_gen) : 'N/A')}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Ultima Connessione</div>
                            <div class="card-value">${formatValue(customer.last_connection_date ? formatDate(customer.last_connection_date) : 'N/A')}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Data Iscrizione Newsletter</div>
                            <div class="card-value">${formatValue(customer.newsletter_date_add ? formatDate(customer.newsletter_date_add) : 'N/A')}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">IP Registrazione Newsletter</div>
                            <div class="card-value">${formatValue(customer.ip_registration_newsletter)}</div>
                        </div>
                        <div class="card-info">
                            <div class="card-label">Giorni Massimi Pagamento</div>
                            <div class="card-value">${formatValue(customer.max_payment_days)}</div>
                        </div>
                    </div>
                    
                    ${otherFields.length > 0 ? `
                    <div class="expandable-section">
                        <button class="expand-btn" onclick="toggleDetails('${detailsId}')">
                            <span class="expand-icon">▼</span> Altri Campi (${otherFields.length})
                        </button>
                        <div id="${detailsId}" class="details-expanded" style="display: none;">
                            ${otherFields.map(field => `
                                <div class="card-info">
                                    <div class="card-label">${field}</div>
                                    <div class="card-value">${formatValue(customer[field])}</div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    ` : ''}
                    
                    <button class="details-btn" onclick="showFullDetailsFromCache('${cacheKey}')">
                        📋 Mostra Dati JSON Completi
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

// Funzioni di utilità
function getOrderStatus(stateId) {
    const statusMap = {
        '1': { text: 'In attesa', class: 'status-pending' },
        '2': { text: 'Pagamento accettato', class: 'status-paid' },
        '3': { text: 'In preparazione', class: 'status-pending' },
        '4': { text: 'Spedito', class: 'status-shipped' },
        '5': { text: 'Consegnato', class: 'status-paid' },
        '6': { text: 'Annullato', class: 'status-pending' },
        '7': { text: 'Rimborsato', class: 'status-pending' },
        '8': { text: 'Errore pagamento', class: 'status-pending' },
    };
    
    return statusMap[stateId] || { text: 'Sconosciuto', class: 'status-pending' };
}

function formatDate(dateString) {
    if (!dateString || dateString === 'N/A') return 'N/A';
    
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('it-IT', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (e) {
        return dateString;
    }
}

// Toggle dettagli espandibili
function toggleDetails(detailsId) {
    const details = document.getElementById(detailsId);
    const button = details.previousElementSibling;
    const icon = button.querySelector('.expand-icon');
    
    if (details.style.display === 'none') {
        details.style.display = 'block';
        icon.textContent = '▲';
    } else {
        details.style.display = 'none';
        icon.textContent = '▼';
    }
}

// Mostra dati JSON completi in una modal (dalla cache)
function showFullDetailsFromCache(cacheKey) {
    const data = detailsCache[cacheKey];
    if (data) {
        showFullDetails(data);
    } else {
        alert('Dati non trovati nella cache');
    }
}

// Mostra dati JSON completi in una modal
function showFullDetails(data) {
    const jsonString = JSON.stringify(data, null, 2);
    
    // Crea modal
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>Dati JSON Completi</h3>
                <button class="modal-close" onclick="this.closest('.modal').remove()">×</button>
            </div>
            <div class="modal-body">
                <pre class="json-display" id="json-content">${jsonString}</pre>
            </div>
            <div class="modal-footer">
                <button class="copy-btn" onclick="copyToClipboard(document.getElementById('json-content').textContent)">📋 Copia</button>
                <button class="close-btn" onclick="this.closest('.modal').remove()">Chiudi</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
    
    // Chiudi cliccando fuori dalla modal
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    });
}

// Copia negli appunti
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        alert('Dati copiati negli appunti!');
    }).catch(err => {
        console.error('Errore nella copia:', err);
        alert('Errore nella copia. Usa Ctrl+C sul testo.');
    });
}

// Debounce per la ricerca ordini (evita troppe chiamate mentre l'utente digita)
function debounceSearch(orderId) {
    clearTimeout(searchTimeout);
    
    // Se il campo è vuoto, mostra tutti gli ordini immediatamente
    if (!orderId.trim()) {
        if (allOrders.length > 0) {
            displayOrders(allOrders);
            document.getElementById('orders-empty').style.display = 'none';
        } else {
            loadOrders();
        }
        return;
    }
    
    // Aspetta 500ms dopo che l'utente smette di digitare
    searchTimeout = setTimeout(() => {
        searchOrder(orderId);
    }, 500);
}

// Carica informazioni di spedizione da ShippyPro
async function loadShippingInfo(shippingNumber, sectionId) {
    const section = document.getElementById(sectionId);
    
    if (!section || !shippingNumber) return;
    
    section.style.display = 'block';
    section.innerHTML = '<div class="shipping-loading">🔄 Caricamento dettagli tracking da ShippyPro...</div>';
    
    try {
        const response = await fetch(`/api/shipping/${encodeURIComponent(shippingNumber)}`);
        const data = await response.json();
        
        if (data.success) {
            let html = '<div class="shipping-details">';
            
            // Mostra errori se presenti (per debug)
            if (data.errors && data.errors.length > 0) {
                html += '<div class="shipping-error-section">';
                html += '<h6>⚠️ Errori API:</h6>';
                data.errors.forEach(err => {
                    html += `<div class="error-item">${err}</div>`;
                });
                if (data.debug) {
                    html += `<div class="debug-info">Debug: ${JSON.stringify(data.debug)}</div>`;
                }
                html += '</div>';
            }
            
            // Mostra prima i dati PrestaShop se disponibili (più affidabili)
            if (data.prestashop_order_full) {
                html += '<div class="shipping-section-item tracking-section"><h5>📦 Dettagli Ordine PrestaShop</h5>';
                html += formatShippingData(data.prestashop_order_full);
                html += '</div>';
            }
            
            // Mostra prima il tracking (più importante)
            const trackingData = data.tracking || data.gettracking;
            if (trackingData && !trackingData.Error) {
                html += '<div class="shipping-section-item tracking-section"><h5>📍 Tracking Completo</h5>';
                html += formatTrackingData(trackingData);
                html += '</div>';
            }
            
            const shipmentData = data.shipment || data.getshipment || data.getshipmentbytransactionid || data.getshipmentbytracking;
            if (shipmentData && !shipmentData.Error) {
                html += '<div class="shipping-section-item"><h5>🚚 Dettagli Spedizione ShippyPro</h5>';
                html += formatShippingData(shipmentData);
                html += '</div>';
            }
            
            const orderData = data.order || data.getorder;
            if (orderData && !orderData.Error) {
                html += '<div class="shipping-section-item"><h5>📋 Dettagli Ordine ShippyPro</h5>';
                html += formatShippingData(orderData);
                html += '</div>';
            }
            
            // Mostra altri dati trovati
            Object.keys(data).forEach(key => {
                if (['success', 'shipping_number', 'order', 'shipment', 'tracking', 
                     'getorder', 'getshipment', 'gettracking', 'getshipmentbytransactionid',
                     'errors', 'note', 'suggestions', 'methods_tried', 'debug'].includes(key.toLowerCase())) {
                    return;
                }
                if (data[key] && typeof data[key] === 'object' && !data[key].Error) {
                    html += `<div class="shipping-section-item"><h5>📦 ${key}</h5>`;
                    html += formatShippingData(data[key]);
                    html += '</div>';
                }
            });
            
            // Mostra note e suggerimenti se presenti
            if (data.note) {
                html += '<div class="help-text">';
                html += `<strong>Nota:</strong> ${data.note}`;
                if (data.suggestions && data.suggestions.length > 0) {
                    html += '<ul style="margin: 10px 0; padding-left: 20px;">';
                    data.suggestions.forEach(suggestion => {
                        html += `<li>${suggestion}</li>`;
                    });
                    html += '</ul>';
                }
                html += '</div>';
            }
            
            if (!data.order && !data.shipment && !data.tracking && !data.getorder && !data.getshipment && !data.gettracking) {
                html += '<div class="empty-state">⚠️ Nessuna informazione disponibile per questa spedizione</div>';
                if (data.methods_tried) {
                    html += `<div class="help-text">Metodi tentati: ${data.methods_tried.join(', ')}</div>`;
                }
            }
            
            html += '</div>';
            section.innerHTML = html;
        } else {
            section.innerHTML = `<div class="empty-state">❌ Errore: ${data.error || 'Errore sconosciuto'}</div>`;
        }
    } catch (error) {
        section.innerHTML = `<div class="empty-state">❌ Errore di connessione: ${error.message}</div>`;
    }
}

// Formatta i dati di tracking in modo più dettagliato
function formatTrackingData(data) {
    if (!data || typeof data !== 'object') {
        return '<div class="empty-state">Nessun dato di tracking disponibile</div>';
    }
    
    let html = '<div class="tracking-details">';
    
    // Cerca campi specifici di tracking
    const trackingFields = ['TrackingNumber', 'TrackingNumber', 'Carrier', 'Status', 'CurrentStatus', 
                           'EstimatedDelivery', 'DeliveryDate', 'Events', 'TrackingEvents', 'History',
                           'Location', 'CurrentLocation', 'Destination', 'Origin', 'Weight', 'Dimensions'];
    
    // Prima mostra i campi di tracking più importanti
    for (const field of trackingFields) {
        if (data[field] !== null && data[field] !== undefined && data[field] !== '') {
            html += `<div class="tracking-field-highlight">
                <div class="tracking-label">${field}</div>
                <div class="tracking-value">${formatTrackingValue(data[field])}</div>
            </div>`;
        }
    }
    
    // Poi mostra tutti gli altri campi
    html += '<div class="tracking-other-fields"><h6>Altri Dettagli:</h6>';
    html += '<div class="shipping-data-grid">';
    
    for (const [key, value] of Object.entries(data)) {
        if (trackingFields.includes(key)) continue;
        if (value === null || value === undefined || value === '') continue;
        
        html += `<div class="shipping-data-item">
            <div class="shipping-label">${key}</div>
            <div class="shipping-value">${formatTrackingValue(value)}</div>
        </div>`;
    }
    
    html += '</div></div></div>';
    return html;
}

// Formatta i valori di tracking
function formatTrackingValue(value) {
    if (typeof value === 'object' && value !== null) {
        if (Array.isArray(value)) {
            if (value.length === 0) return 'Nessun evento';
            let html = '<div class="tracking-events">';
            value.forEach((event, index) => {
                html += `<div class="tracking-event-item">
                    <div class="event-number">#${index + 1}</div>
                    <div class="event-details">${formatShippingData({...event})}</div>
                </div>`;
            });
            html += '</div>';
            return html;
        } else {
            return JSON.stringify(value, null, 2);
        }
    }
    return value;
}

// Formatta i dati di spedizione per la visualizzazione
function formatShippingData(data) {
    if (!data || typeof data !== 'object') {
        return '<div class="empty-state">Nessun dato disponibile</div>';
    }
    
    let html = '<div class="shipping-data-grid">';
    
    for (const [key, value] of Object.entries(data)) {
        if (value === null || value === undefined || value === '') continue;
        
        let displayValue = value;
        if (typeof value === 'object') {
            displayValue = JSON.stringify(value, null, 2);
            html += `<div class="shipping-data-item full-width"><div class="shipping-label">${key}</div><pre class="shipping-value-json">${displayValue}</pre></div>`;
        } else if (typeof value === 'boolean') {
            displayValue = value ? 'Sì' : 'No';
            html += `<div class="shipping-data-item"><div class="shipping-label">${key}</div><div class="shipping-value">${displayValue}</div></div>`;
        } else {
            html += `<div class="shipping-data-item"><div class="shipping-label">${key}</div><div class="shipping-value">${displayValue}</div></div>`;
        }
    }
    
    html += '</div>';
    return html;
}

// Carica ordini all'avvio
document.addEventListener('DOMContentLoaded', () => {
    loadOrders();
});


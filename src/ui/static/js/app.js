// GoQuant Trade Simulator - JavaScript Application

class TradeSimulatorApp {
    constructor() {
        this.websocket = null;
        this.isConnected = false;
        this.marketData = {};
        this.statistics = {};
        this.retryCount = 0;
        this.maxRetries = 5;
        
        // Chart data tracking
        this.costHistory = [];
        this.charts = {};
        this.maxHistoryPoints = 20;
        
        this.initializeElements();
        this.setupEventListeners();
        this.initializeCharts();
        this.connectWebSocket();
        this.startPeriodicUpdates();
    }

    initializeElements() {
        // Connection status elements
        this.connectionIndicator = document.getElementById('connection-indicator');
        this.connectionText = document.getElementById('connection-text');
        
        // Market data elements
        this.symbolElement = document.getElementById('symbol');
        this.bidPriceElement = document.getElementById('bid-price');
        this.askPriceElement = document.getElementById('ask-price');
        this.midPriceElement = document.getElementById('mid-price');
        this.spreadElement = document.getElementById('spread');
        this.spreadBpsElement = document.getElementById('spread-bps');
        
        // Form elements
        this.tradeForm = document.getElementById('trade-form');
        this.tradeSizeInput = document.getElementById('trade-size');
        this.orderTypeSelect = document.getElementById('order-type');
        this.sideSelect = document.getElementById('side');
        this.limitPriceInput = document.getElementById('limit-price');
        this.timeHorizonInput = document.getElementById('time-horizon');
        
        // Results elements
        this.resultsContent = document.getElementById('results-content');
        
        // Statistics elements
        this.totalTradesElement = document.getElementById('total-trades');
        this.avgProcessingTimeElement = document.getElementById('avg-processing-time');
        this.marketUpdatesElement = document.getElementById('market-updates');
        this.modelStatusElement = document.getElementById('model-status');
        
        // Loading and modal elements
        this.loadingOverlay = document.getElementById('loading-overlay');
        this.errorModal = document.getElementById('error-modal');
        this.errorMessage = document.getElementById('error-message');
    }

    setupEventListeners() {
        // Form submission
        this.tradeForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.calculateTradeCost();
        });

        // Order type change
        this.orderTypeSelect.addEventListener('change', () => {
            this.toggleLimitPrice();
        });

        // Side change
        this.sideSelect.addEventListener('change', () => {
            this.toggleLimitPrice();
        });

        // Debounced input validation
        const debouncedValidation = this.debounce(() => {
            this.validateForm();
        }, 300);

        this.tradeSizeInput.addEventListener('input', debouncedValidation);
        this.timeHorizonInput.addEventListener('input', debouncedValidation);
        this.limitPriceInput.addEventListener('input', debouncedValidation);
    }

    connectWebSocket() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('✅ WebSocket connected');
                this.isConnected = true;
                this.retryCount = 0;
                this.updateConnectionStatus('connected', 'Connected');
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleWebSocketMessage(message);
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error);
                }
            };
            
            this.websocket.onclose = () => {
                console.log('🔌 WebSocket disconnected');
                this.isConnected = false;
                this.updateConnectionStatus('connecting', 'Connecting...');
                this.scheduleReconnect();
            };
            
            this.websocket.onerror = (error) => {
                console.error('❌ WebSocket error:', error);
                this.isConnected = false;
                this.updateConnectionStatus('error', 'Connection Error');
            };
            
        } catch (error) {
            console.error('❌ Failed to create WebSocket connection:', error);
            this.updateConnectionStatus('error', 'Connection Error');
        }
    }

    scheduleReconnect() {
        if (this.retryCount < this.maxRetries) {
            this.retryCount++;
            const delay = Math.min(1000 * Math.pow(2, this.retryCount), 30000);
            
            this.updateConnectionStatus('connecting', `Reconnecting in ${delay/1000}s...`);
            
            setTimeout(() => {
                this.updateConnectionStatus('connecting', 'Connecting...');
                this.connectWebSocket();
            }, delay);
        } else {
            this.updateConnectionStatus('offline', 'Connection Failed');
            this.showError('WebSocket connection failed after multiple attempts. Please refresh the page.');
        }
    }

    handleWebSocketMessage(message) {
        switch (message.type) {
            case 'market_update':
                this.handleMarketUpdate(message.data);
                break;
            case 'cost_estimate':
                console.log('📊 Received cost estimate via WebSocket:', message.data);
                this.displayCostEstimate(message.data);
                break;
            case 'error':
                console.error('❌ WebSocket error message:', message.data);
                this.showError(message.data.message || 'WebSocket error occurred');
                break;
            default:
                console.log('📨 Unknown WebSocket message type:', message.type);
        }
    }

    updateConnectionStatus(status, text) {
        this.connectionIndicator.className = `connection-indicator ${status}`;
        this.connectionText.textContent = text;
    }

    handleMarketUpdate(data) {
        this.marketData = { ...this.marketData, ...data };
        
        if (data.symbol) {
            this.symbolElement.textContent = data.symbol;
        }
        
        if (data.bid_price) {
            this.bidPriceElement.textContent = this.formatPrice(data.bid_price);
        }
        
        if (data.ask_price) {
            this.askPriceElement.textContent = this.formatPrice(data.ask_price);
        }
        
        if (data.mid_price) {
            this.midPriceElement.textContent = this.formatPrice(data.mid_price);
        }
        
        if (data.spread) {
            this.spreadElement.textContent = this.formatPrice(data.spread);
        }
        
        if (data.spread_bps) {
            this.spreadBpsElement.textContent = data.spread_bps.toFixed(2);
        }
        
        // Update limit price suggestion for limit orders
        if (this.orderTypeSelect.value === 'limit' && !this.limitPriceInput.value) {
            if (this.sideSelect.value === 'buy' && data.bid_price) {
                this.limitPriceInput.value = data.bid_price;
            } else if (this.sideSelect.value === 'sell' && data.ask_price) {
                this.limitPriceInput.value = data.ask_price;
            }
        }
    }

    toggleLimitPrice() {
        const isLimit = this.orderTypeSelect.value === 'limit';
        this.limitPriceInput.disabled = !isLimit;
        
        if (isLimit && this.marketData.bid_price && this.marketData.ask_price) {
            // Set reasonable default based on side
            if (this.sideSelect.value === 'buy') {
                this.limitPriceInput.value = this.marketData.bid_price;
            } else {
                this.limitPriceInput.value = this.marketData.ask_price;
            }
        } else if (!isLimit) {
            this.limitPriceInput.value = '';
        }
    }

    async calculateTradeCost() {
        console.log('=== calculateTradeCost called ===');
        console.log('🔗 Connection status:', this.isConnected);
        
        // Remove WebSocket dependency - work with HTTP API only
        const tradeData = this.getTradeParameters();
        if (!tradeData) return;

        this.showLoading(true);

        try {
            console.log('🚀 Sending trade request:', tradeData);

            // Send HTTP request
            const response = await fetch('/api/estimate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(tradeData)
            });

            console.log('📡 Response status:', response.status);
            console.log('📡 Response headers:', response.headers);

            if (!response.ok) {
                const errorText = await response.text();
                console.error('❌ Error response text:', errorText);
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }

            const result = await response.json();
            console.log('📊 API Response:', result);
            console.log('📊 Response type:', typeof result);
            console.log('📊 Response keys:', Object.keys(result));
            
            this.displayCostEstimate(result);

        } catch (error) {
            console.error('❌ Error calculating trade cost:', error);
            console.error('❌ Error stack:', error.stack);
            this.showError(`Error: ${error.message}`);
        } finally {
            this.showLoading(false);
        }
    }

    getTradeParameters() {
        const tradeSizeValue = this.tradeSizeInput.value.trim();
        const timeHorizonValue = this.timeHorizonInput.value.trim();
        
        const tradeSize = parseFloat(tradeSizeValue);
        const orderType = this.orderTypeSelect.value;
        const side = this.sideSelect.value;
        const timeHorizon = parseFloat(timeHorizonValue);
        
        console.log('🔍 Validating parameters:', {
            tradeSizeValue, tradeSize, 
            timeHorizonValue, timeHorizon, 
            orderType, side
        });
        
        if (isNaN(tradeSize) || tradeSize <= 0) {
            this.showError('Please enter a valid trade size.');
            return null;
        }
        
        if (isNaN(timeHorizon) || timeHorizon <= 0) {
            this.showError('Please enter a valid time horizon.');
            return null;
        }

        const params = {
            trade_size: tradeSize,
            order_type: orderType,
            side: side,
            time_horizon: timeHorizon
        };

        if (orderType === 'limit') {
            const limitPriceValue = this.limitPriceInput.value.trim();
            const limitPrice = parseFloat(limitPriceValue);
            if (isNaN(limitPrice) || limitPrice <= 0) {
                this.showError('Please enter a valid limit price.');
                return null;
            }
            params.limit_price = limitPrice;
        }

        console.log('✅ Final parameters:', params);
        return params;
    }

    displayCostEstimate(data) {
        console.log('=== displayCostEstimate called ===');
        console.log('📊 Received cost estimate data:', data);
        console.log('🔍 Data type:', typeof data);
        console.log('🔑 Data keys:', data ? Object.keys(data) : 'no data');
        
        // Check if data has the required structure
        if (!data || typeof data !== 'object') {
            console.error('❌ Invalid data type:', typeof data);
            this.showError('Invalid cost estimate data received - no data object.');
            return;
        }
        
        // Handle the API response format directly
        if (!data.cost_breakdown) {
            console.error('❌ No cost_breakdown in data. Available keys:', Object.keys(data));
            console.error('📄 Full data object:', JSON.stringify(data, null, 2));
            this.showError('Invalid cost estimate data received - no cost breakdown.');
            return;
        }
        
        console.log('✅ Cost breakdown found:', data.cost_breakdown);

        const costBreakdown = data.cost_breakdown;
        
        // Validate cost breakdown fields
        if (typeof costBreakdown.total_cost === 'undefined' || 
            typeof costBreakdown.exchange_fee === 'undefined' ||
            typeof costBreakdown.slippage_cost === 'undefined' ||
            typeof costBreakdown.market_impact === 'undefined') {
            console.error('❌ Missing cost breakdown fields:', costBreakdown);
            this.showError('Invalid cost estimate data received - incomplete cost breakdown.');
            return;
        }
        
        // API returns dollar amounts directly, no conversion needed
        const totalCostUSD = parseFloat(costBreakdown.total_cost) || 0;
        const exchangeFeeUSD = parseFloat(costBreakdown.exchange_fee) || 0;
        const slippageCostUSD = parseFloat(costBreakdown.slippage_cost) || 0;
        const marketImpactUSD = parseFloat(costBreakdown.market_impact) || 0;
        const costBps = parseFloat(costBreakdown.cost_bps) || 0;
        
        console.log('💰 Parsed costs:', {
            totalCostUSD, exchangeFeeUSD, slippageCostUSD, marketImpactUSD, costBps
        });
        
        // Create results HTML
        const html = `
            <div class="cost-breakdown fade-in">
                <div class="cost-item total">
                    <span class="cost-label">Total Cost</span>
                    <span class="cost-value">$${totalCostUSD.toFixed(2)} (${costBps.toFixed(1)} bps)</span>
                </div>
                
                <div class="cost-item fee">
                    <span class="cost-label">Exchange Fee</span>
                    <span class="cost-value">$${exchangeFeeUSD.toFixed(2)}</span>
                </div>
                
                <div class="cost-item slippage">
                    <span class="cost-label">Slippage Cost</span>
                    <span class="cost-value">$${slippageCostUSD.toFixed(2)}</span>
                </div>
                
                <div class="cost-item impact">
                    <span class="cost-label">Market Impact</span>
                    <span class="cost-value">$${marketImpactUSD.toFixed(2)}</span>
                </div>
            </div>
            
            <div class="probabilities fade-in">
                <div class="probability-item">
                    <div class="probability-value">${(data.probabilities.maker_probability * 100).toFixed(1)}%</div>
                    <div class="probability-label">Maker Probability</div>
                </div>
                <div class="probability-item">
                    <div class="probability-value">${(data.probabilities.slippage_confidence * 100).toFixed(1)}%</div>
                    <div class="probability-label">Slippage Confidence</div>
                </div>
            </div>
            
            <div class="market-conditions fade-in">
                <h4>Market Conditions</h4>
                <div class="conditions-grid">
                    <div class="condition-item">
                        <div class="condition-value">${this.formatPrice(data.market_conditions.bid_ask_spread)}</div>
                        <div class="condition-label">Spread</div>
                    </div>
                    <div class="condition-item">
                        <div class="condition-value">${data.market_conditions.market_depth.toFixed(2)}</div>
                        <div class="condition-label">Market Depth</div>
                    </div>
                    <div class="condition-item">
                        <div class="condition-value">${(data.market_conditions.volatility * 100).toFixed(2)}%</div>
                        <div class="condition-label">Volatility</div>
                    </div>
                    <div class="condition-item">
                        <div class="condition-value">${this.formatPrice(data.current_price)}</div>
                        <div class="condition-label">Current Price</div>
                    </div>
                </div>
            </div>
            
            <div class="strategy-recommendation fade-in">
                <h4>Optimal Strategy</h4>
                <div class="strategy-value">${data.optimal_strategy}</div>
            </div>
        `;
        
        this.resultsContent.innerHTML = html;
        console.log('✅ Results HTML updated successfully');
        
        // Update charts with new data
        this.updateCharts(data);
    }

    initializeCharts() {
        console.log('🎨 Initializing charts...');
        
        // Chart.js default configuration
        Chart.defaults.color = '#ffffff';
        Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.1)';
        Chart.defaults.backgroundColor = 'rgba(255, 255, 255, 0.05)';
        
        this.initializeCostBreakdownChart();
        this.initializeCostHistoryChart();
        this.initializeProbabilityChart();
        this.initializeMarketConditionsChart();
        
        console.log('✅ Charts initialized successfully');
    }

    initializeCostBreakdownChart() {
        const ctx = document.getElementById('costBreakdownChart').getContext('2d');
        this.charts.costBreakdown = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Exchange Fee', 'Slippage Cost', 'Market Impact'],
                datasets: [{
                    data: [0, 0, 0],
                    backgroundColor: [
                        '#00d4ff',
                        '#ff6b6b',
                        '#4ecdc4'
                    ],
                    borderColor: [
                        '#00a3cc',
                        '#cc5555',
                        '#3ea9a0'
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#ffffff',
                            padding: 15,
                            font: {
                                size: 12
                            }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.label + ': $' + context.parsed.toFixed(2);
                            }
                        }
                    }
                }
            }
        });
    }

    initializeCostHistoryChart() {
        const ctx = document.getElementById('costHistoryChart').getContext('2d');
        this.charts.costHistory = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Total Cost ($)',
                    data: [],
                    borderColor: '#00d4ff',
                    backgroundColor: 'rgba(0, 212, 255, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }, {
                    label: 'Cost (bps)',
                    data: [],
                    borderColor: '#ff6b6b',
                    backgroundColor: 'rgba(255, 107, 107, 0.1)',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.4,
                    yAxisID: 'y1'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: '#ffffff',
                            font: {
                                size: 11
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: '#888',
                            maxTicksLimit: 8
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        ticks: {
                            color: '#00d4ff'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        ticks: {
                            color: '#ff6b6b'
                        },
                        grid: {
                            drawOnChartArea: false
                        }
                    }
                }
            }
        });
    }

    initializeProbabilityChart() {
        const ctx = document.getElementById('probabilityChart').getContext('2d');
        this.charts.probability = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Maker Probability', 'Slippage Confidence'],
                datasets: [{
                    label: 'Probability (%)',
                    data: [0, 0],
                    backgroundColor: [
                        'rgba(0, 212, 255, 0.8)',
                        'rgba(78, 205, 196, 0.8)'
                    ],
                    borderColor: [
                        '#00d4ff',
                        '#4ecdc4'
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    x: {
                        ticks: {
                            color: '#ffffff'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            color: '#ffffff',
                            callback: function(value) {
                                return value + '%';
                            }
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                }
            }
        });
    }

    initializeMarketConditionsChart() {
        const ctx = document.getElementById('marketConditionsChart').getContext('2d');
        this.charts.marketConditions = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: ['Spread', 'Depth', 'Volatility', 'Volume'],
                datasets: [{
                    label: 'Market Conditions',
                    data: [0, 0, 0, 0],
                    backgroundColor: 'rgba(0, 212, 255, 0.2)',
                    borderColor: '#00d4ff',
                    borderWidth: 2,
                    pointBackgroundColor: '#00d4ff',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    r: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            color: '#888',
                            backdropColor: 'transparent'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        angleLines: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        pointLabels: {
                            color: '#ffffff'
                        }
                    }
                }
            }
        });
    }

    async startPeriodicUpdates() {
        // Update statistics every 5 seconds
        setInterval(async () => {
            try {
                await this.updateStatistics();
            } catch (error) {
                console.error('Error updating statistics:', error);
            }
        }, 5000);
    }

    async updateStatistics() {
        try {
            const response = await fetch('/api/status');
            if (response.ok) {
                const stats = await response.json();
                this.updateStatisticsDisplay(stats);
            }
        } catch (error) {
            console.error('Error fetching statistics:', error);
        }
    }

    updateStatisticsDisplay(stats) {
        this.totalTradesElement.textContent = stats.trade_count || 0;
        this.avgProcessingTimeElement.textContent = stats.avg_processing_time ? 
            `${stats.avg_processing_time.toFixed(2)} ms` : '-- ms';
        this.marketUpdatesElement.textContent = stats.market_updates || 0;
        
        // Update model status
        if (stats.models && stats.models.all_models_trained) {
            this.modelStatusElement.textContent = 'All Models Trained';
            this.modelStatusElement.className = 'status trained';
        } else {
            this.modelStatusElement.textContent = 'Training In Progress';
            this.modelStatusElement.className = 'status training';
        }
    }

    validateForm() {
        const tradeSize = parseFloat(this.tradeSizeInput.value);
        const timeHorizon = parseFloat(this.timeHorizonInput.value);
        
        let isValid = true;
        
        if (isNaN(tradeSize) || tradeSize <= 0) {
            isValid = false;
        }
        
        if (isNaN(timeHorizon) || timeHorizon <= 0) {
            isValid = false;
        }
        
        if (this.orderTypeSelect.value === 'limit') {
            const limitPrice = parseFloat(this.limitPriceInput.value);
            if (isNaN(limitPrice) || limitPrice <= 0) {
                isValid = false;
            }
        }
        
        return isValid;
    }

    showLoading(show) {
        this.loadingOverlay.style.display = show ? 'flex' : 'none';
    }

    showError(message) {
        console.error('🚨 Showing error:', message);
        this.errorMessage.textContent = message;
        this.errorModal.style.display = 'block';
    }

    formatPrice(price) {
        if (price == null) return '--';
        return parseFloat(price).toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 8
        });
    }

    debounce(func, wait) {
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
}

// Global functions for modal handling
function closeErrorModal() {
    document.getElementById('error-modal').style.display = 'none';
}

// Close modal when clicking outside of it
window.onclick = function(e) {
    const modal = document.getElementById('error-modal');
    if (e.target === modal) {
        modal.style.display = 'none';
    }
}

// Handle page visibility changes
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        console.log('Page hidden, maintaining WebSocket connection');
    } else {
        console.log('Page visible, checking WebSocket connection');
        if (window.app && !window.app.isConnected) {
            window.app.connectWebSocket();
        }
    }
});

// Initialize the application when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Initializing GoQuant Trade Simulator...');
    window.app = new TradeSimulatorApp();
});

// Chart update methods for GoQuant Trade Simulator

// Add these methods to the TradeSimulatorApp class

function updateCharts(data) {
    console.log('📊 Updating charts with new data...');
    
    try {
        this.updateCostBreakdownChart(data.cost_breakdown);
        this.updateCostHistoryChart(data);
        this.updateProbabilityChart(data.probabilities);
        this.updateMarketConditionsChart(data.market_conditions);
        
        console.log('✅ Charts updated successfully');
    } catch (error) {
        console.error('❌ Error updating charts:', error);
    }
}

function updateCostBreakdownChart(costBreakdown) {
    if (!this.charts.costBreakdown || !costBreakdown) return;
    
    const chart = this.charts.costBreakdown;
    chart.data.datasets[0].data = [
        parseFloat(costBreakdown.exchange_fee) || 0,
        parseFloat(costBreakdown.slippage_cost) || 0,
        parseFloat(costBreakdown.market_impact) || 0
    ];
    chart.update('none');
}

function updateCostHistoryChart(data) {
    if (!this.charts.costHistory || !data.cost_breakdown) return;
    
    const chart = this.charts.costHistory;
    const now = new Date().toLocaleTimeString();
    
    this.costHistory.push({
        timestamp: now,
        totalCost: parseFloat(data.cost_breakdown.total_cost) || 0,
        costBps: parseFloat(data.cost_breakdown.cost_bps) || 0
    });
    
    if (this.costHistory.length > this.maxHistoryPoints) {
        this.costHistory.shift();
    }
    
    chart.data.labels = this.costHistory.map(item => item.timestamp);
    chart.data.datasets[0].data = this.costHistory.map(item => item.totalCost);
    chart.data.datasets[1].data = this.costHistory.map(item => item.costBps);
    
    chart.update('none');
}

function updateProbabilityChart(probabilities) {
    if (!this.charts.probability || !probabilities) return;
    
    const chart = this.charts.probability;
    chart.data.datasets[0].data = [
        (parseFloat(probabilities.maker_probability) || 0) * 100,
        (parseFloat(probabilities.slippage_confidence) || 0) * 100
    ];
    chart.update('none');
}

function updateMarketConditionsChart(marketConditions) {
    if (!this.charts.marketConditions || !marketConditions) return;
    
    const chart = this.charts.marketConditions;
    
    const normalizedData = [
        Math.min((parseFloat(marketConditions.bid_ask_spread) || 0) * 10000, 100),
        Math.min((parseFloat(marketConditions.market_depth) || 0), 100),
        Math.min((parseFloat(marketConditions.volatility) || 0) * 1000, 100),
        Math.min(((parseFloat(marketConditions.volume_24h) || 1000000) / 10000000) * 100, 100)
    ];
    
    chart.data.datasets[0].data = normalizedData;
    chart.update('none');
}

// Assign methods to TradeSimulatorApp prototype
if (typeof TradeSimulatorApp !== 'undefined') {
    TradeSimulatorApp.prototype.updateCharts = updateCharts;
    TradeSimulatorApp.prototype.updateCostBreakdownChart = updateCostBreakdownChart;
    TradeSimulatorApp.prototype.updateCostHistoryChart = updateCostHistoryChart;
    TradeSimulatorApp.prototype.updateProbabilityChart = updateProbabilityChart;
    TradeSimulatorApp.prototype.updateMarketConditionsChart = updateMarketConditionsChart;
}

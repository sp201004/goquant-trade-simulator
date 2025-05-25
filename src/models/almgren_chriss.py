"""
Almgren-Chriss model implementation for market impact calculation.
Used to estimate the market impact of large trades over time.
"""

import numpy as np
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from scipy.optimize import minimize
import logging

# Use standard logging instead of custom logger for now
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

@dataclass
class AlmgrenChrissParams:
    """Parameters for the Almgren-Chriss model."""
    sigma: float  # Volatility of the asset
    gamma: float  # Risk aversion parameter
    eta: float    # Permanent market impact parameter
    epsilon: float  # Temporary market impact parameter
    tau: float    # Total trading time
    
    def __post_init__(self):
        """Validate parameters."""
        if self.sigma <= 0:
            raise ValueError("Volatility (sigma) must be positive")
        if self.gamma <= 0:
            raise ValueError("Risk aversion (gamma) must be positive")
        if self.eta < 0:
            raise ValueError("Permanent impact (eta) must be non-negative")
        if self.epsilon < 0:
            raise ValueError("Temporary impact (epsilon) must be non-negative")
        if self.tau <= 0:
            raise ValueError("Trading time (tau) must be positive")


@dataclass
class TradingSchedule:
    """Optimal trading schedule from Almgren-Chriss model."""
    times: np.ndarray          # Time points
    holdings: np.ndarray       # Holdings at each time point
    trade_rates: np.ndarray    # Trading rates at each time point
    expected_cost: float       # Expected implementation shortfall
    variance: float           # Variance of implementation shortfall
    utility: float            # Expected utility


class AlmgrenChrissModel:
    """
    Almgren-Chriss optimal execution model.
    
    This model provides the optimal trading strategy that minimizes
    the expected implementation shortfall plus a risk penalty.
    """
    
    def __init__(self, params: AlmgrenChrissParams):
        self.params = params
        self._kappa = None  # Will be calculated
        
    def _calculate_kappa(self) -> float:
        """Calculate the kappa parameter."""
        return np.sqrt(self.params.gamma * self.params.sigma**2 / self.params.eta)
        
    def calculate_optimal_strategy(
        self, 
        initial_position: float, 
        n_intervals: int = 100
    ) -> TradingSchedule:
        """
        Calculate the optimal trading strategy.
        
        Args:
            initial_position: Initial position to liquidate (positive for selling)
            n_intervals: Number of time intervals
            
        Returns:
            TradingSchedule with optimal strategy
        """
        self._kappa = self._calculate_kappa()
        
        # Time grid
        dt = self.params.tau / n_intervals
        times = np.linspace(0, self.params.tau, n_intervals + 1)
        
        # Calculate optimal holdings trajectory
        holdings = np.zeros(n_intervals + 1)
        trade_rates = np.zeros(n_intervals)
        
        for i, t in enumerate(times):
            remaining_time = self.params.tau - t
            if remaining_time > 0:
                holdings[i] = initial_position * np.sinh(self._kappa * remaining_time) / np.sinh(self._kappa * self.params.tau)
            else:
                holdings[i] = 0
                
        # Calculate trading rates
        for i in range(n_intervals):
            trade_rates[i] = -(holdings[i+1] - holdings[i]) / dt
            
        # Calculate expected cost and variance
        expected_cost = self._calculate_expected_cost(initial_position, trade_rates, dt)
        variance = self._calculate_variance(initial_position, trade_rates, dt)
        utility = expected_cost + 0.5 * self.params.gamma * variance
        
        return TradingSchedule(
            times=times,
            holdings=holdings,
            trade_rates=trade_rates,
            expected_cost=expected_cost,
            variance=variance,
            utility=utility
        )
        
    def _calculate_expected_cost(
        self, 
        initial_position: float, 
        trade_rates: np.ndarray, 
        dt: float
    ) -> float:
        """Calculate expected implementation shortfall."""
        # Permanent impact cost
        permanent_cost = 0.5 * self.params.eta * initial_position**2
        
        # Temporary impact cost
        temporary_cost = self.params.epsilon * np.sum(trade_rates**2) * dt
        
        return permanent_cost + temporary_cost
        
    def _calculate_variance(
        self, 
        initial_position: float, 
        trade_rates: np.ndarray, 
        dt: float
    ) -> float:
        """Calculate variance of implementation shortfall."""
        # This is a simplified calculation
        # In practice, this would involve more complex stochastic calculus
        return self.params.sigma**2 * initial_position**2 * self.params.tau / 3
        
    def calculate_market_impact(
        self, 
        trade_size: float, 
        current_time: float, 
        strategy: TradingSchedule
    ) -> Dict[str, float]:
        """
        Calculate market impact for a given trade.
        
        Args:
            trade_size: Size of the trade
            current_time: Current time in the strategy
            strategy: The trading strategy being executed
            
        Returns:
            Dictionary with impact components
        """
        # Find closest time point in strategy
        time_idx = np.argmin(np.abs(strategy.times - current_time))
        
        # Permanent impact
        permanent_impact = self.params.eta * trade_size
        
        # Temporary impact
        temporary_impact = self.params.epsilon * trade_size
        
        # Total impact
        total_impact = permanent_impact + temporary_impact
        
        return {
            "permanent_impact": permanent_impact,
            "temporary_impact": temporary_impact,
            "total_impact": total_impact,
            "impact_bps": total_impact * 10000  # In basis points
        }
        
    def optimize_parameters(
        self, 
        historical_trades: List[Dict[str, Any]], 
        price_data: np.ndarray
    ) -> AlmgrenChrissParams:
        """
        Optimize model parameters based on historical data.
        
        Args:
            historical_trades: List of historical trade data
            price_data: Historical price data for volatility estimation
            
        Returns:
            Optimized parameters
        """
        # Estimate volatility from price data
        returns = np.diff(np.log(price_data))
        sigma = np.std(returns) * np.sqrt(len(returns))  # Annualized volatility
        
        # Initial parameter guess
        initial_params = [
            0.1,   # gamma
            0.001, # eta
            0.01,  # epsilon
            1.0    # tau
        ]
        
        def objective(params):
            """Objective function for parameter optimization."""
            try:
                gamma, eta, epsilon, tau = params
                if any(p <= 0 for p in params):
                    return 1e6
                    
                model_params = AlmgrenChrissParams(
                    sigma=sigma,
                    gamma=gamma,
                    eta=eta,
                    epsilon=epsilon,
                    tau=tau
                )
                
                temp_model = AlmgrenChrissModel(model_params)
                
                # Calculate error between model predictions and actual trades
                total_error = 0
                for trade in historical_trades:
                    predicted_impact = temp_model.calculate_market_impact(
                        trade['size'], 
                        trade['time'], 
                        temp_model.calculate_optimal_strategy(trade['initial_position'])
                    )
                    actual_impact = trade.get('actual_impact', 0)
                    total_error += (predicted_impact['total_impact'] - actual_impact)**2
                    
                return total_error
                
            except Exception:
                return 1e6
                
        # Optimize parameters
        result = minimize(
            objective, 
            initial_params, 
            method='L-BFGS-B',
            bounds=[(1e-6, 10), (1e-6, 1), (1e-6, 1), (0.1, 10)]
        )
        
        if result.success:
            gamma, eta, epsilon, tau = result.x
            return AlmgrenChrissParams(
                sigma=sigma,
                gamma=gamma,
                eta=eta,
                epsilon=epsilon,
                tau=tau
            )
        else:
            logger.warning("Parameter optimization failed, using default values")
            return AlmgrenChrissParams(
                sigma=sigma,
                gamma=0.1,
                eta=0.001,
                epsilon=0.01,
                tau=1.0
            )


class AdaptiveAlmgrenChriss:
    """
    Adaptive version of Almgren-Chriss model that updates parameters
    based on real-time market conditions.
    """
    
    def __init__(self, initial_params: AlmgrenChrissParams, adaptation_rate: float = 0.1):
        self.current_params = initial_params
        self.adaptation_rate = adaptation_rate
        self.model = AlmgrenChrissModel(initial_params)
        self._recent_trades: List[Dict[str, Any]] = []
        self._max_history = 100
        
    def update_with_trade(self, trade_data: Dict[str, Any]) -> None:
        """Update model with new trade data."""
        self._recent_trades.append(trade_data)
        
        # Keep only recent trades
        if len(self._recent_trades) > self._max_history:
            self._recent_trades = self._recent_trades[-self._max_history:]
            
        # Periodically re-optimize parameters
        if len(self._recent_trades) % 10 == 0:
            self._adapt_parameters()
            
    def _adapt_parameters(self) -> None:
        """Adapt parameters based on recent trade performance."""
        if len(self._recent_trades) < 10:
            return
            
        try:
            # Extract price data from recent trades
            prices = np.array([trade['price'] for trade in self._recent_trades])
            
            # Re-optimize parameters
            new_params = self.model.optimize_parameters(self._recent_trades, prices)
            
            # Smoothly update current parameters
            self.current_params.gamma = (
                (1 - self.adaptation_rate) * self.current_params.gamma + 
                self.adaptation_rate * new_params.gamma
            )
            self.current_params.eta = (
                (1 - self.adaptation_rate) * self.current_params.eta + 
                self.adaptation_rate * new_params.eta
            )
            self.current_params.epsilon = (
                (1 - self.adaptation_rate) * self.current_params.epsilon + 
                self.adaptation_rate * new_params.epsilon
            )
            
            # Update model with new parameters
            self.model = AlmgrenChrissModel(self.current_params)
            
            logger.info(f"Adapted Almgren-Chriss parameters: gamma={self.current_params.gamma:.4f}, "
                       f"eta={self.current_params.eta:.6f}, epsilon={self.current_params.epsilon:.4f}")
                       
        except Exception as e:
            logger.error(f"Failed to adapt parameters: {e}")
            
    def calculate_optimal_strategy(self, initial_position: float, n_intervals: int = 100) -> TradingSchedule:
        """Calculate optimal strategy with current parameters."""
        return self.model.calculate_optimal_strategy(initial_position, n_intervals)
        
    def calculate_market_impact(self, trade_size: float, current_time: float, strategy: TradingSchedule) -> Dict[str, float]:
        """Calculate market impact with current parameters."""
        return self.model.calculate_market_impact(trade_size, current_time, strategy)

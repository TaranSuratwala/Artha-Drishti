# import torch
# import torch.nn as nn
# import numpy as np
# import pandas as pd
# import os
# import joblib
# from sklearn.preprocessing import MinMaxScaler
# from sklearn.model_selection import TimeSeriesSplit
# from torch.utils.data import DataLoader, TensorDataset
# from FeatureEngineering import StockFeatureEngineer

# MODEL_DIR = "saved_models"
# if not os.path.exists(MODEL_DIR):
#     os.makedirs(MODEL_DIR)

# # --- ADVANCED ARCHITECTURE: LSTM + Multi-Head Attention ---
# class AttentionLSTM(nn.Module):
#     """
#     Hybrid architecture combining LSTM's sequential processing 
#     with Transformer's attention mechanism for better predictions
#     """
#     def __init__(self, input_dim, hidden_dim=128, num_layers=3, dropout=0.3, num_heads=8):
#         super(AttentionLSTM, self).__init__()
        
#         self.hidden_dim = hidden_dim
#         self.num_layers = num_layers
        
#         # Bidirectional LSTM for capturing both forward and backward dependencies
#         self.lstm = nn.LSTM(
#             input_dim, 
#             hidden_dim, 
#             num_layers, 
#             batch_first=True, 
#             dropout=dropout if num_layers > 1 else 0,
#             bidirectional=True
#         )
        
#         # Multi-head attention layer
#         self.attention = nn.MultiheadAttention(
#             embed_dim=hidden_dim * 2,  # *2 for bidirectional
#             num_heads=num_heads,
#             dropout=dropout,
#             batch_first=True
#         )
        
#         # Layer normalization
#         self.layer_norm1 = nn.LayerNorm(hidden_dim * 2)
#         self.layer_norm2 = nn.LayerNorm(hidden_dim * 2)
        
#         # Feed-forward network
#         self.fc1 = nn.Linear(hidden_dim * 2, hidden_dim)
#         self.fc2 = nn.Linear(hidden_dim, hidden_dim // 2)
#         self.fc_out = nn.Linear(hidden_dim // 2, 1)
        
#         self.dropout = nn.Dropout(dropout)
#         self.relu = nn.ReLU()
        
#     def forward(self, x):
#         # LSTM processing
#         lstm_out, _ = self.lstm(x)  # Shape: (batch, seq, hidden*2)
        
#         # Self-attention
#         attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)
#         attn_out = self.layer_norm1(lstm_out + attn_out)  # Residual connection
        
#         # Take the last time step
#         last_hidden = attn_out[:, -1, :]
        
#         # Feed-forward network with residual
#         ff_out = self.fc1(last_hidden)
#         ff_out = self.relu(ff_out)
#         ff_out = self.dropout(ff_out)
        
#         ff_out = self.fc2(ff_out)
#         ff_out = self.relu(ff_out)
#         ff_out = self.dropout(ff_out)
        
#         output = self.fc_out(ff_out)
#         return output


# class EnsemblePredictor(nn.Module):
#     """Ensemble of multiple models for robust predictions"""
#     def __init__(self, input_dim, hidden_dim=128):
#         super(EnsemblePredictor, self).__init__()
        
#         # Model 1: Attention LSTM
#         self.model1 = AttentionLSTM(input_dim, hidden_dim=hidden_dim, num_layers=3, dropout=0.3)
        
#         # Model 2: Simple Transformer
#         encoder_layer = nn.TransformerEncoderLayer(
#             d_model=hidden_dim, 
#             nhead=8, 
#             dropout=0.3, 
#             batch_first=True
#         )
#         self.fc_in = nn.Linear(input_dim, hidden_dim)
#         self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=2)
#         self.fc_transformer = nn.Linear(hidden_dim, 1)
        
#         # Ensemble combiner
#         self.combiner = nn.Linear(2, 1)
        
#     def forward(self, x):
#         # Get prediction from LSTM model
#         pred1 = self.model1(x)
        
#         # Get prediction from Transformer
#         x_transformed = torch.relu(self.fc_in(x))
#         transformer_out = self.transformer(x_transformed)
#         pred2 = self.fc_transformer(transformer_out[:, -1, :])
        
#         # Combine predictions
#         combined = torch.cat([pred1, pred2], dim=1)
#         final_pred = self.combiner(combined)
        
#         return final_pred


# class EnhancedStockPredictor:
#     def __init__(self, pipeline):
#         self.pipeline = pipeline
#         self.model = None
#         self.scaler = None
#         self.SEQ_LEN = 60  # 60 days lookback
#         self.PRED_DAYS = 5  # 5 days ahead prediction
        
#     def _get_paths(self, ticker):
#         return (
#             f"{MODEL_DIR}/{ticker}_enhanced_model.pth", 
#             f"{MODEL_DIR}/{ticker}_scaler.pkl",
#             f"{MODEL_DIR}/{ticker}_metrics.pkl"
#         )
    
#     def prepare_data(self, ticker):
#         """Enhanced data preparation with more features"""
#         raw_data = self.pipeline.get_ticker_history(ticker)
#         df = pd.DataFrame(raw_data)
#         if df.empty or len(df) < 300:  # Need more data for robust training
#             return None
        
#         # Add technical indicators
#         engineer = StockFeatureEngineer(df)
#         df = engineer.add_technical_indicators()
#         df = engineer.add_price_patterns()
        
#         # Add fundamental data
#         fund, sentiment = engineer.get_sentiment_and_fundamentals(ticker + ".NS")
#         for key, val in fund.items(): 
#             df[key] = val
#         df['sentiment'] = sentiment
        
#         # Add custom features
#         df['price_momentum_5'] = df['close'].pct_change(5)
#         df['price_momentum_10'] = df['close'].pct_change(10)
#         df['price_momentum_20'] = df['close'].pct_change(20)
#         df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
#         df['volatility'] = df['close'].rolling(20).std()
        
#         # Add day of week and month features
#         df['date'] = pd.to_datetime(df['date'])
#         df['day_of_week'] = df['date'].dt.dayofweek
#         df['month'] = df['date'].dt.month
        
#         df = df.dropna().reset_index(drop=True)
#         return df
    
#     def get_tensors(self, df, is_training=True):
#         """Prepare tensors with validation split"""
#         _, scaler_path, _ = self._get_paths(df['ticker'].iloc[0])
#         feature_cols = [c for c in df.columns if c not in ['date', 'ticker']]
#         data_values = df[feature_cols].values
        
#         if is_training:
#             self.scaler = MinMaxScaler(feature_range=(0, 1))
#             scaled_data = self.scaler.fit_transform(data_values)
#             joblib.dump(self.scaler, scaler_path)
#         else:
#             if os.path.exists(scaler_path):
#                 self.scaler = joblib.load(scaler_path)
#                 scaled_data = self.scaler.transform(data_values)
#             else:
#                 self.scaler = MinMaxScaler(feature_range=(0, 1))
#                 scaled_data = self.scaler.fit_transform(data_values)
        
#         X, y = [], []
#         target_col_idx = df.columns.get_loc('close') - 2
#         limit = len(scaled_data) - self.PRED_DAYS
        
#         for i in range(self.SEQ_LEN, limit):
#             X.append(scaled_data[i-self.SEQ_LEN:i])
#             y.append(scaled_data[i+self.PRED_DAYS, target_col_idx])
        
#         if len(X) == 0: 
#             return None, None, None, None
        
#         X = torch.FloatTensor(np.array(X))
#         y = torch.FloatTensor(np.array(y)).view(-1, 1)
        
#         # Split into train and validation
#         split_idx = int(len(X) * 0.85)
#         X_train, X_val = X[:split_idx], X[split_idx:]
#         y_train, y_val = y[:split_idx], y[split_idx:]
        
#         return X_train, y_train, X_val, y_val
    
#     def train_with_validation(self, ticker, force_retrain=False, use_ensemble=False):
#         """Enhanced training with validation and early stopping"""
#         df = self.prepare_data(ticker)
#         if df is None: 
#             return {"status": "error", "message": "Insufficient data"}
        
#         model_path, _, metrics_path = self._get_paths(ticker)
#         model_exists = os.path.exists(model_path)
#         is_fresh_start = force_retrain or not model_exists
        
#         X_train, y_train, X_val, y_val = self.get_tensors(df, is_training=is_fresh_start)
#         if X_train is None: 
#             return {"status": "error", "message": "Data preparation failed"}
        
#         input_dim = X_train.shape[2]
        
#         # Choose model architecture
#         if use_ensemble:
#             self.model = EnsemblePredictor(input_dim=input_dim, hidden_dim=128)
#         else:
#             self.model = AttentionLSTM(input_dim=input_dim, hidden_dim=128, num_layers=3, dropout=0.3)
        
#         # Load existing model if updating
#         if not is_fresh_start and model_exists:
#             try:
#                 self.model.load_state_dict(torch.load(model_path))
#                 print(f"🔄 Updating {ticker} model...")
#             except:
#                 print(f"🚀 Retraining {ticker} model (incompatible saved model)...")
#                 is_fresh_start = True
#         else:
#             print(f"🚀 Training NEW model for {ticker}...")
        
#         # Training configuration
#         if is_fresh_start:
#             optimizer = torch.optim.AdamW(self.model.parameters(), lr=0.001, weight_decay=1e-5)
#             scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
#                 optimizer, mode='min', factor=0.5, patience=3, verbose=True
#             )
#             epochs = 50
#         else:
#             optimizer = torch.optim.AdamW(self.model.parameters(), lr=0.0001, weight_decay=1e-5)
#             scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
#                 optimizer, mode='min', factor=0.5, patience=2, verbose=True
#             )
#             epochs = 20
        
#         criterion = nn.MSELoss()
#         train_loader = DataLoader(TensorDataset(X_train, y_train), batch_size=32, shuffle=True)
#         val_loader = DataLoader(TensorDataset(X_val, y_val), batch_size=32, shuffle=False)
        
#         # Early stopping
#         best_val_loss = float('inf')
#         patience = 10
#         patience_counter = 0
#         best_model_state = None
        
#         train_losses = []
#         val_losses = []
        
#         for epoch in range(epochs):
#             # Training phase
#             self.model.train()
#             train_loss = 0
#             for batch_X, batch_y in train_loader:
#                 optimizer.zero_grad()
#                 outputs = self.model(batch_X)
#                 loss = criterion(outputs, batch_y)
#                 loss.backward()
#                 torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
#                 optimizer.step()
#                 train_loss += loss.item()
            
#             avg_train_loss = train_loss / len(train_loader)
#             train_losses.append(avg_train_loss)
            
#             # Validation phase
#             self.model.eval()
#             val_loss = 0
#             with torch.no_grad():
#                 for batch_X, batch_y in val_loader:
#                     outputs = self.model(batch_X)
#                     loss = criterion(outputs, batch_y)
#                     val_loss += loss.item()
            
#             avg_val_loss = val_loss / len(val_loader)
#             val_losses.append(avg_val_loss)
            
#             # Learning rate scheduling
#             scheduler.step(avg_val_loss)
            
#             # Early stopping check
#             if avg_val_loss < best_val_loss:
#                 best_val_loss = avg_val_loss
#                 best_model_state = self.model.state_dict().copy()
#                 patience_counter = 0
#             else:
#                 patience_counter += 1
            
#             if (epoch + 1) % 5 == 0:
#                 print(f"Epoch {epoch+1}/{epochs} - Train Loss: {avg_train_loss:.5f}, Val Loss: {avg_val_loss:.5f}")
            
#             if patience_counter >= patience:
#                 print(f"Early stopping at epoch {epoch+1}")
#                 break
        
#         # Load best model
#         if best_model_state:
#             self.model.load_state_dict(best_model_state)
        
#         # Save model
#         torch.save(self.model.state_dict(), model_path)
        
#         # Save training metrics
#         metrics = {
#             'train_losses': train_losses,
#             'val_losses': val_losses,
#             'best_val_loss': best_val_loss,
#             'final_epoch': epoch + 1
#         }
#         joblib.dump(metrics, metrics_path)
        
#         return {
#             "status": "success",
#             "message": f"Training completed for {ticker}",
#             "best_val_loss": round(best_val_loss, 5),
#             "epochs_trained": epoch + 1
#         }
    
#     def predict(self, ticker, capital=100000, risk_pct=2.0, use_ensemble=False):
#         """Enhanced prediction with confidence intervals"""
#         model_path, scaler_path, metrics_path = self._get_paths(ticker)
        
#         if not os.path.exists(model_path):
#             return {"error": "Model not trained yet. Please train the model first."}
        
#         df = self.prepare_data(ticker)
#         if df is None:
#             return {"error": "Insufficient data for prediction"}
        
#         # Load scaler
#         self.scaler = joblib.load(scaler_path)
#         feature_cols = [c for c in df.columns if c not in ['date', 'ticker']]
        
#         data_values = df[feature_cols].values
#         scaled_data = self.scaler.transform(data_values)
        
#         # Prepare input sequence
#         last_seq = scaled_data[-self.SEQ_LEN:]
#         last_seq_tensor = torch.FloatTensor(last_seq).unsqueeze(0)
        
#         # Load model
#         input_dim = last_seq.shape[1]
#         if use_ensemble:
#             self.model = EnsemblePredictor(input_dim=input_dim, hidden_dim=128)
#         else:
#             self.model = AttentionLSTM(input_dim=input_dim, hidden_dim=128, num_layers=3, dropout=0.3)
        
#         self.model.load_state_dict(torch.load(model_path))
#         self.model.eval()
        
#         # Monte Carlo dropout for uncertainty estimation
#         predictions = []
#         self.model.train()  # Enable dropout
#         with torch.no_grad():
#             for _ in range(20):  # 20 forward passes
#                 pred = self.model(last_seq_tensor).item()
#                 predictions.append(pred)
#         self.model.eval()
        
#         # Statistics
#         pred_mean = np.mean(predictions)
#         pred_std = np.std(predictions)
        
#         # Inverse transform
#         dummy = np.zeros((1, len(feature_cols)))
#         target_idx = df.columns.get_loc('close') - 2
        
#         dummy[0, target_idx] = pred_mean
#         pred_price = self.scaler.inverse_transform(dummy)[0, target_idx]
        
#         # Confidence interval
#         dummy[0, target_idx] = pred_mean - pred_std
#         pred_lower = self.scaler.inverse_transform(dummy)[0, target_idx]
        
#         dummy[0, target_idx] = pred_mean + pred_std
#         pred_upper = self.scaler.inverse_transform(dummy)[0, target_idx]
        
#         # Current price and risk metrics
#         current_price = df['close'].iloc[-1]
#         atr = df['ATRr_14'].iloc[-1] if 'ATRr_14' in df.columns else (current_price * 0.02)
        
#         # Risk management
#         stop_loss = current_price - (2.5 * atr)
#         target_price = pred_price
        
#         risk_per_share = current_price - stop_loss
#         reward_per_share = target_price - current_price
#         rr_ratio = reward_per_share / risk_per_share if risk_per_share > 0 else 0
        
#         predicted_return = ((pred_price - current_price) / current_price) * 100
        
#         # Position sizing
#         max_loss_amount = float(capital) * (float(risk_pct) / 100.0)
        
#         if risk_per_share > 0 and predicted_return > 0 and rr_ratio > 1.5:
#             suggested_qty = int(max_loss_amount / risk_per_share)
#         else:
#             suggested_qty = 0
        
#         trade_value = suggested_qty * current_price
        
#         # Signal generation with stricter criteria
#         signal = "HOLD"
#         confidence = "LOW"
        
#         if predicted_return > 3.0 and rr_ratio > 2.0:
#             signal = "BUY"
#             confidence = "HIGH" if predicted_return > 5.0 else "MEDIUM"
#         elif predicted_return > 1.5 and rr_ratio > 1.5:
#             signal = "BUY"
#             confidence = "MEDIUM"
#         elif predicted_return < -3.0:
#             signal = "SELL"
#             confidence = "HIGH" if predicted_return < -5.0 else "MEDIUM"
        
#         # Load training metrics
#         metrics = joblib.load(metrics_path) if os.path.exists(metrics_path) else {}
        
#         return {
#             "ticker": ticker,
#             "current_price": round(current_price, 2),
#             "predicted_price_5d": round(pred_price, 2),
#             "predicted_return_pct": round(predicted_return, 2),
#             "prediction_confidence": confidence,
#             "confidence_interval": {
#                 "lower": round(pred_lower, 2),
#                 "upper": round(pred_upper, 2)
#             },
#             "signal": signal,
#             "stop_loss": round(stop_loss, 2),
#             "target_price": round(target_price, 2),
#             "risk_reward_ratio": round(rr_ratio, 2),
#             "suggested_quantity": suggested_qty,
#             "risk_per_share": round(risk_per_share, 2),
#             "trade_value": round(trade_value, 2),
#             "max_loss_amount": round(max_loss_amount, 2),
#             "model_metrics": {
#                 "validation_loss": round(metrics.get('best_val_loss', 0), 5),
#                 "epochs_trained": metrics.get('final_epoch', 0)
#             }
#         }











# import torch
# import torch.nn as nn
# import torch.nn.functional as F
# import numpy as np
# import pandas as pd
# import os
# import joblib
# import logging
# from sklearn.preprocessing import RobustScaler
# from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
# from torch.utils.data import DataLoader, TensorDataset
# from sqlalchemy import create_engine, text
# from FeatureEngineering import StockFeatureEngineer
# from typing import Dict, List, Optional, Tuple
# from datetime import datetime
# import warnings
# from tqdm import tqdm
# import matplotlib.pyplot as plt
# import seaborn as sns
# from collections import defaultdict
# import json
# import time
# import sys

# warnings.filterwarnings('ignore')

# # Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler('ml_prediction.log', encoding='utf-8'),
#         logging.StreamHandler()
#     ]
# )
# # Fix encoding for Windows console
# if sys.platform == 'win32':
#     sys.stdout.reconfigure(encoding='utf-8')
#     sys.stderr.reconfigure(encoding='utf-8')
    
# logger = logging.getLogger(__name__)

# # --- CONFIGURATION ---
# MODEL_DIR = "saved_models"
# METRICS_DIR = "performance_metrics"
# PLOTS_DIR = "performance_plots"
# DB_URL = "postgresql://postgres:Taran%4017@localhost:5432/StockDB"

# for directory in [MODEL_DIR, METRICS_DIR, PLOTS_DIR]:
#     if not os.path.exists(directory):
#         os.makedirs(directory)


# # ==================== ENHANCED NEURAL ARCHITECTURES ====================

# class WaveNetBlock(nn.Module):
#     """WaveNet-style dilated causal convolution block"""
#     def __init__(self, in_channels, out_channels, dilation):
#         super(WaveNetBlock, self).__init__()
#         self.conv = nn.Conv1d(in_channels, out_channels, kernel_size=2, 
#                               dilation=dilation, padding=dilation)
#         self.norm = nn.BatchNorm1d(out_channels)
#         self.gate_conv = nn.Conv1d(in_channels, out_channels, kernel_size=2,
#                                    dilation=dilation, padding=dilation)
#         self.gate_norm = nn.BatchNorm1d(out_channels)
        
#     def forward(self, x):
#         residual = x
#         x_conv = torch.tanh(self.norm(self.conv(x)))
#         x_gate = torch.sigmoid(self.gate_norm(self.gate_conv(x)))
#         out = x_conv * x_gate
        
#         # Residual connection
#         if residual.shape == out.shape:
#             out = out + residual
#         return out


# class ImprovedLSTMModel(nn.Module):
#     """Enhanced LSTM with attention and proper normalization"""
#     def __init__(self, input_dim, hidden_dim=128, num_layers=3, dropout=0.25):
#         super(ImprovedLSTMModel, self).__init__()
        
#         self.hidden_dim = hidden_dim
#         self.num_layers = num_layers
        
#         # Feature projection
#         self.input_proj = nn.Linear(input_dim, hidden_dim)
#         self.input_norm = nn.LayerNorm(hidden_dim)
        
#         # Stacked Bi-LSTM
#         self.lstm = nn.LSTM(
#             hidden_dim,
#             hidden_dim,
#             num_layers,
#             batch_first=True,
#             dropout=dropout if num_layers > 1 else 0,
#             bidirectional=True
#         )
        
#         # Multi-head attention
#         self.attention = nn.MultiheadAttention(
#             embed_dim=hidden_dim * 2,
#             num_heads=4,
#             dropout=dropout,
#             batch_first=True
#         )
        
#         self.norm1 = nn.LayerNorm(hidden_dim * 2)
#         self.norm2 = nn.LayerNorm(hidden_dim * 2)
        
#         # Feed-forward network
#         self.ff = nn.Sequential(
#             nn.Linear(hidden_dim * 2, hidden_dim * 4),
#             nn.GELU(),
#             nn.Dropout(dropout),
#             nn.Linear(hidden_dim * 4, hidden_dim * 2)
#         )
        
#         # Output head
#         self.output = nn.Sequential(
#             nn.Linear(hidden_dim * 2, hidden_dim),
#             nn.LayerNorm(hidden_dim),
#             nn.GELU(),
#             nn.Dropout(dropout),
#             nn.Linear(hidden_dim, hidden_dim // 2),
#             nn.LayerNorm(hidden_dim // 2),
#             nn.GELU(),
#             nn.Dropout(dropout),
#             nn.Linear(hidden_dim // 2, 1)
#         )
        
#     def forward(self, x):
#         # Project and normalize input
#         x = self.input_proj(x)
#         x = self.input_norm(x)
        
#         # LSTM
#         lstm_out, _ = self.lstm(x)
        
#         # Self-attention with residual
#         attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)
#         x = self.norm1(lstm_out + attn_out)
        
#         # Feed-forward with residual
#         ff_out = self.ff(x)
#         x = self.norm2(x + ff_out)
        
#         # Use last timestep
#         x = x[:, -1, :]
        
#         # Output
#         output = self.output(x)
#         return output


# class TemporalConvNet(nn.Module):
#     """Temporal Convolutional Network with WaveNet blocks"""
#     def __init__(self, input_dim, hidden_dim=128, num_blocks=4, dropout=0.25):
#         super(TemporalConvNet, self).__init__()
        
#         self.input_conv = nn.Conv1d(input_dim, hidden_dim, kernel_size=1)
        
#         # WaveNet blocks with increasing dilation
#         self.blocks = nn.ModuleList([
#             WaveNetBlock(hidden_dim, hidden_dim, dilation=2**i)
#             for i in range(num_blocks)
#         ])
        
#         self.output = nn.Sequential(
#             nn.AdaptiveAvgPool1d(1),
#             nn.Flatten(),
#             nn.Linear(hidden_dim, hidden_dim // 2),
#             nn.LayerNorm(hidden_dim // 2),
#             nn.GELU(),
#             nn.Dropout(dropout),
#             nn.Linear(hidden_dim // 2, 1)
#         )
        
#     def forward(self, x):
#         # x: (batch, seq, features)
#         x = x.transpose(1, 2)  # (batch, features, seq)
#         x = self.input_conv(x)
        
#         for block in self.blocks:
#             x = block(x)
        
#         output = self.output(x)
#         return output


# class TransformerModel(nn.Module):
#     """Transformer encoder for time series"""
#     def __init__(self, input_dim, d_model=128, nhead=8, num_layers=3, dropout=0.25):
#         super(TransformerModel, self).__init__()
        
#         self.input_proj = nn.Linear(input_dim, d_model)
#         self.pos_encoder = nn.Parameter(torch.randn(1, 1000, d_model) * 0.02)
        
#         encoder_layer = nn.TransformerEncoderLayer(
#             d_model=d_model,
#             nhead=nhead,
#             dim_feedforward=d_model * 4,
#             dropout=dropout,
#             activation='gelu',
#             batch_first=True,
#             norm_first=True
#         )
#         self.transformer = nn.TransformerEncoder(encoder_layer, num_layers)
        
#         self.output = nn.Sequential(
#             nn.Linear(d_model, d_model // 2),
#             nn.LayerNorm(d_model // 2),
#             nn.GELU(),
#             nn.Dropout(dropout),
#             nn.Linear(d_model // 2, 1)
#         )
        
#     def forward(self, x):
#         seq_len = x.size(1)
#         x = self.input_proj(x)
#         x = x + self.pos_encoder[:, :seq_len, :]
#         x = self.transformer(x)
#         output = self.output(x[:, -1, :])
#         return output


# class AdvancedEnsemble(nn.Module):
#     """
#     Advanced ensemble combining LSTM, TCN, and Transformer
#     with learned attention-based weighting
#     """
#     def __init__(self, input_dim, hidden_dim=128):
#         super(AdvancedEnsemble, self).__init__()
        
#         self.lstm = ImprovedLSTMModel(input_dim, hidden_dim, num_layers=3, dropout=0.25)
#         self.tcn = TemporalConvNet(input_dim, hidden_dim, num_blocks=4, dropout=0.25)
#         self.transformer = TransformerModel(input_dim, d_model=hidden_dim, nhead=8, num_layers=3, dropout=0.25)
        
#         # Attention-based ensemble
#         self.ensemble_attention = nn.Sequential(
#             nn.Linear(3, 8),
#             nn.ReLU(),
#             nn.Linear(8, 3),
#             nn.Softmax(dim=-1)
#         )
        
#     def forward(self, x):
#         pred1 = self.lstm(x)
#         pred2 = self.tcn(x)
#         pred3 = self.transformer(x)
        
#         # Stack predictions
#         # FIX: Use torch.cat instead of stack+squeeze to handle batch_size=1 correctly
#         preds = torch.cat([pred1, pred2, pred3], dim=1)  # (batch, 3)
        
#         # Learned weights
#         weights = self.ensemble_attention(preds)  # (batch, 3)
        
#         # Weighted combination
#         output = torch.sum(weights * preds, dim=1, keepdim=True)
        
#         return output


# # ==================== PERFORMANCE ANALYZER ====================

# class PerformanceAnalyzer:
#     """Comprehensive performance analysis"""
    
#     def __init__(self, save_dir: str = METRICS_DIR):
#         self.save_dir = save_dir
    
#     def calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict:
#         """Calculate comprehensive metrics"""
#         mse = mean_squared_error(y_true, y_pred)
#         rmse = np.sqrt(mse)
#         mae = mean_absolute_error(y_true, y_pred)
#         r2 = r2_score(y_true, y_pred)
        
#         # Directional accuracy
#         y_true_dir = np.sign(np.diff(y_true, prepend=y_true[0]))
#         y_pred_dir = np.sign(np.diff(y_pred, prepend=y_pred[0]))
#         dir_acc = np.mean(y_true_dir == y_pred_dir) * 100
        
#         # MAPE with safety
#         mape = np.mean(np.abs((y_true - y_pred) / (np.abs(y_true) + 1e-8))) * 100
        
#         return {
#             'mse': float(mse),
#             'rmse': float(rmse),
#             'mae': float(mae),
#             'r2_score': float(r2),
#             'directional_accuracy': float(dir_acc),
#             'mape': float(mape),
#             'max_error': float(np.max(np.abs(y_true - y_pred)))
#         }
    
#     def plot_results(self, train_losses, val_losses, actuals, preds, ticker):
#         """Plot comprehensive results"""
#         fig = plt.figure(figsize=(18, 10))
#         gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)
        
#         # Loss curves
#         ax1 = fig.add_subplot(gs[0, :])
#         ax1.plot(train_losses, label='Train Loss', linewidth=2, alpha=0.8)
#         ax1.plot(val_losses, label='Validation Loss', linewidth=2, alpha=0.8)
#         ax1.set_title(f'{ticker} - Training History', fontsize=14, fontweight='bold')
#         ax1.set_xlabel('Epoch')
#         ax1.set_ylabel('MSE Loss')
#         ax1.legend()
#         ax1.grid(True, alpha=0.3)
#         ax1.set_yscale('log')
        
#         # Predictions
#         ax2 = fig.add_subplot(gs[1, :])
#         ax2.plot(actuals, label='Actual', linewidth=2, alpha=0.7, color='blue')
#         ax2.plot(preds, label='Predicted', linewidth=2, alpha=0.7, color='red')
#         ax2.set_title(f'{ticker} - Actual vs Predicted', fontsize=14, fontweight='bold')
#         ax2.set_xlabel('Time Steps')
#         ax2.set_ylabel('Scaled Price')
#         ax2.legend()
#         ax2.grid(True, alpha=0.3)
        
#         # Error distribution
#         errors = actuals - preds
#         ax3 = fig.add_subplot(gs[2, 0])
#         ax3.hist(errors, bins=50, alpha=0.7, color='green', edgecolor='black')
#         ax3.axvline(0, color='red', linestyle='--', linewidth=2)
#         ax3.set_title('Prediction Error Distribution')
#         ax3.set_xlabel('Error')
#         ax3.set_ylabel('Frequency')
#         ax3.grid(True, alpha=0.3)
        
#         # Scatter plot
#         ax4 = fig.add_subplot(gs[2, 1])
#         ax4.scatter(actuals, preds, alpha=0.5, s=20)
#         min_val = min(actuals.min(), preds.min())
#         max_val = max(actuals.max(), preds.max())
#         ax4.plot([min_val, max_val], [min_val, max_val], 'r--', linewidth=2)
#         ax4.set_title('Actual vs Predicted Scatter')
#         ax4.set_xlabel('Actual')
#         ax4.set_ylabel('Predicted')
#         ax4.grid(True, alpha=0.3)
        
#         plt.savefig(f"{PLOTS_DIR}/{ticker}_comprehensive.png", dpi=300, bbox_inches='tight')
#         plt.close()


# # ==================== PRODUCTION PREDICTOR ====================

# class ProductionStockPredictor:
#     """
#     Production-ready stock predictor with state-of-the-art performance
#     """
    
#     def __init__(self, db_url: str = DB_URL):
#         self.db_url = db_url
#         self.engine = create_engine(db_url, pool_pre_ping=True)
#         self.model = None
#         self.scaler = None
#         self.feature_cols = None
#         self.performance_analyzer = PerformanceAnalyzer()
        
#         # Optimized hyperparameters
#         self.SEQ_LEN = 40
#         self.PRED_DAYS = 5
#         self.MIN_DATA_POINTS = 400
#         self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
#         logger.info(f"[OK] Initialized on device: {self.device}")
    
#     def _get_paths(self, ticker: str) -> Tuple[str, str, str, str]:
#         return (
#             f"{MODEL_DIR}/{ticker}_model.pth",
#             f"{MODEL_DIR}/{ticker}_scaler.pkl",
#             f"{MODEL_DIR}/{ticker}_metrics.pkl",
#             f"{MODEL_DIR}/{ticker}_features.pkl"
#         )
    
#     def get_stock_data(self, ticker: str) -> pd.DataFrame:
#         """Fetch stock data"""
#         query = text("""
#             SELECT date, open, high, low, close, volume, adj_close
#             FROM nse_stocks 
#             WHERE ticker = :ticker 
#             ORDER BY date ASC
#         """)
#         try:
#             df = pd.read_sql(query, self.engine, params={'ticker': ticker})
#             return df
#         except Exception as e:
#             logger.error(f"Error fetching {ticker}: {e}")
#             return pd.DataFrame()
    
#     def prepare_data(self, ticker: str) -> Optional[pd.DataFrame]:
#         """Enhanced data preparation"""
#         raw_data = self.get_stock_data(ticker)
        
#         if raw_data.empty or len(raw_data) < self.MIN_DATA_POINTS:
#             logger.warning(f"Insufficient data for {ticker}: {len(raw_data)} rows")
#             return None
        
#         try:
#             # Feature engineering
#             engineer = StockFeatureEngineer(raw_data, ticker=ticker)
#             df = engineer.build_features(
#                 include_fundamentals=False,
#                 include_sentiment=False,
#                 include_targets=False
#             )
            
#             # Ensure ticker column is preserved
#             if 'ticker' not in df.columns:
#                 df['ticker'] = ticker
            
#             # Additional technical features
#             df['price_momentum_3'] = df['close'].pct_change(3)
#             df['price_momentum_7'] = df['close'].pct_change(7)
#             df['price_momentum_14'] = df['close'].pct_change(14)
#             df['price_momentum_21'] = df['close'].pct_change(21)
            
#             df['volatility_7'] = df['close'].pct_change().rolling(7).std()
#             df['volatility_14'] = df['close'].pct_change().rolling(14).std()
#             df['volatility_21'] = df['close'].pct_change().rolling(21).std()
            
#             df['volume_ma_7'] = df['volume'].rolling(7).mean()
#             df['volume_ma_14'] = df['volume'].rolling(14).mean()
#             df['volume_std_7'] = df['volume'].rolling(7).std()
            
#             # Price position features
#             df['price_to_high_20'] = df['close'] / df['high'].rolling(20).max()
#             df['price_to_low_20'] = df['close'] / df['low'].rolling(20).min()
            
#             # Handle missing values
#             df = df.replace([np.inf, -np.inf], np.nan)
            
#             # Forward fill then backward fill
#             df = df.ffill().bfill()
            
#             # Drop remaining NaN rows
#             df = df.dropna()
            
#             if len(df) < self.MIN_DATA_POINTS:
#                 logger.warning(f"Insufficient data after cleaning for {ticker}: {len(df)} rows")
#                 return None
            
#             logger.info(f"Prepared {len(df)} rows for {ticker}")
#             return df
            
#         except Exception as e:
#             logger.error(f"Error preparing {ticker}: {e}")
#             return None
    
#     def create_sequences(self, df: pd.DataFrame, is_training: bool = True) -> Tuple:
#         """Create sequences with proper validation"""
#         ticker = df['ticker'].iloc[0] if 'ticker' in df.columns else 'UNKNOWN'
#         model_path, scaler_path, _, feature_path = self._get_paths(ticker)
        
#         # Select features
#         exclude_cols = ['date', 'ticker'] + [c for c in df.columns if c.startswith('target_')]
#         all_cols = [c for c in df.columns if c not in exclude_cols]
        
#         if 'close' not in all_cols:
#             logger.error("'close' column not found!")
#             return None, None, None, None
        
#         # Put close as first column
#         feature_cols = ['close'] + [c for c in all_cols if c != 'close']
        
#         data_values = df[feature_cols].values
        
#         # Scaling
#         if is_training:
#             self.scaler = RobustScaler()
#             scaled_data = self.scaler.fit_transform(data_values)
            
#             # Store feature columns in instance variable BEFORE saving
#             self.feature_cols = feature_cols
            
#             # Ensure directory exists
#             os.makedirs(MODEL_DIR, exist_ok=True)
            
#             # Save with explicit error handling
#             try:
#                 # Use protocol 4 for compatibility
#                 with open(scaler_path, 'wb') as f:
#                     joblib.dump(self.scaler, f, compress=3)
#                 with open(feature_path, 'wb') as f:
#                     joblib.dump(feature_cols, f, compress=3)
                
#                 # Force OS to write to disk
#                 if hasattr(os, 'sync'):
#                     os.sync()
                
#                 # Verify immediately
#                 time.sleep(0.2)
#                 scaler_exists = os.path.exists(scaler_path) and os.path.getsize(scaler_path) > 0
#                 features_exists = os.path.exists(feature_path) and os.path.getsize(feature_path) > 0
                
#                 if scaler_exists and features_exists:
#                     logger.info(f"[OK] Saved scaler ({os.path.getsize(scaler_path)} bytes) and features ({os.path.getsize(feature_path)} bytes)")
#                     # Don't set read-only - it causes issues with verification
#                 else:
#                     logger.error(f"[ERROR] File save failed - Scaler: {scaler_exists}, Features: {features_exists}")
                    
#             except Exception as e:
#                 logger.error(f"[ERROR] Exception saving files: {e}")
#                 raise
#         else:
#             if os.path.exists(scaler_path) and os.path.exists(feature_path):
#                 self.scaler = joblib.load(scaler_path)
#                 saved_features = joblib.load(feature_path)
#                 self.feature_cols = saved_features
#                 if saved_features != feature_cols:
#                     logger.error("Feature mismatch!")
#                     return None, None, None, None
#                 scaled_data = self.scaler.transform(data_values)
#             else:
#                 logger.error("Scaler or features not found!")
#                 return None, None, None, None
        
#         # Create sequences
#         X, y = [], []
#         target_idx = 0  # close is first column
        
#         for i in range(self.SEQ_LEN, len(scaled_data) - self.PRED_DAYS):
#             X.append(scaled_data[i - self.SEQ_LEN:i])
#             y.append(scaled_data[i + self.PRED_DAYS, target_idx])
        
#         if len(X) == 0:
#             logger.error("No sequences created!")
#             return None, None, None, None
        
#         X = torch.FloatTensor(np.array(X))
#         y = torch.FloatTensor(np.array(y)).view(-1, 1)
        
#         # Time-based split (85-15 for more training data)
#         split_idx = int(len(X) * 0.85)
#         X_train, X_val = X[:split_idx], X[split_idx:]
#         y_train, y_val = y[:split_idx], y[split_idx:]
        
#         logger.info(f"Sequences created - Train: {len(X_train)}, Val: {len(X_val)}, Features: {X_train.shape[2]}")
        
#         return X_train, y_train, X_val, y_val
    
#     def train(self, ticker: str, force_retrain: bool = False, 
#               model_type: str = 'ensemble', epochs: int = 150,
#               learning_rate: float = 0.001) -> Dict:
#         """
#         Train model with advanced techniques
        
#         Args:
#             ticker: Stock ticker
#             force_retrain: Retrain from scratch
#             model_type: 'lstm', 'tcn', 'transformer', or 'ensemble'
#             epochs: Maximum epochs
#             learning_rate: Initial learning rate
#         """
        
#         logger.info("="*70)
#         logger.info(f"TRAINING: {ticker} (Model: {model_type})")
#         logger.info("="*70)
        
#         # Prepare data
#         df = self.prepare_data(ticker)
#         if df is None:
#             return {"status": "error", "message": "Data preparation failed"}
        
#         # Ensure ticker is in dataframe
#         if 'ticker' not in df.columns:
#             df['ticker'] = ticker
        
#         model_path, scaler_path, metrics_path, feature_path = self._get_paths(ticker)
        
#         # Create sequences - pass ticker explicitly
#         X_train, y_train, X_val, y_val = self.create_sequences(df, is_training=True)
#         if X_train is None:
#             return {"status": "error", "message": "Sequence creation failed"}
        
#         input_dim = X_train.shape[2]
        
#         # Initialize model
#         if model_type == 'lstm':
#             self.model = ImprovedLSTMModel(input_dim, hidden_dim=128, num_layers=3, dropout=0.25)
#         elif model_type == 'tcn':
#             self.model = TemporalConvNet(input_dim, hidden_dim=128, num_blocks=4, dropout=0.25)
#         elif model_type == 'transformer':
#             self.model = TransformerModel(input_dim, d_model=128, nhead=8, num_layers=3, dropout=0.25)
#         else:  # ensemble
#             self.model = AdvancedEnsemble(input_dim, hidden_dim=128)
        
#         self.model = self.model.to(self.device)
        
#         # Training configuration
#         criterion = nn.MSELoss()
#         optimizer = torch.optim.AdamW(self.model.parameters(), lr=learning_rate, weight_decay=1e-4)
        
#         # Cosine annealing with warm restarts
#         scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
#             optimizer, T_0=20, T_mult=2, eta_min=1e-6
#         )
        
#         # Data loaders
#         train_loader = DataLoader(TensorDataset(X_train, y_train), batch_size=32, shuffle=True)
#         val_loader = DataLoader(TensorDataset(X_val, y_val), batch_size=32, shuffle=False)
        
#         # Training loop
#         best_val_loss = float('inf')
#         best_r2 = float('-inf')
#         patience = 30
#         patience_counter = 0
#         best_model_state = None
        
#         train_losses = []
#         val_losses = []
        
#         for epoch in range(epochs):
#             # Training
#             self.model.train()
#             train_loss = 0
#             for batch_X, batch_y in train_loader:
#                 batch_X = batch_X.to(self.device)
#                 batch_y = batch_y.to(self.device)
                
#                 optimizer.zero_grad()
#                 outputs = self.model(batch_X)
#                 loss = criterion(outputs, batch_y)
#                 loss.backward()
#                 torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
#                 optimizer.step()
                
#                 train_loss += loss.item()
            
#             avg_train_loss = train_loss / len(train_loader)
#             train_losses.append(avg_train_loss)
            
#             # Validation
#             self.model.eval()
#             val_loss = 0
#             val_preds = []
#             val_actuals = []
            
#             with torch.no_grad():
#                 for batch_X, batch_y in val_loader:
#                     batch_X = batch_X.to(self.device)
#                     batch_y = batch_y.to(self.device)
                    
#                     outputs = self.model(batch_X)
#                     loss = criterion(outputs, batch_y)
#                     val_loss += loss.item()
                    
#                     val_preds.extend(outputs.cpu().numpy().flatten())
#                     val_actuals.extend(batch_y.cpu().numpy().flatten())
            
#             avg_val_loss = val_loss / len(val_loader)
#             val_losses.append(avg_val_loss)
            
#             val_preds = np.array(val_preds)
#             val_actuals = np.array(val_actuals)
            
#             # Calculate R2 for better model selection
#             current_r2 = r2_score(val_actuals, val_preds)
            
#             scheduler.step()
            
#             # Model selection based on both loss and R2
#             improvement = False
#             if avg_val_loss < best_val_loss * 0.99 or current_r2 > best_r2:
#                 best_val_loss = min(avg_val_loss, best_val_loss)
#                 best_r2 = max(current_r2, best_r2)
#                 best_model_state = self.model.state_dict().copy()
#                 patience_counter = 0
#                 improvement = True
#             else:
#                 patience_counter += 1
            
#             if (epoch + 1) % 10 == 0 or improvement:
#                 logger.info(f"Epoch {epoch+1:3d}/{epochs} | Train: {avg_train_loss:.6f} | "
#                            f"Val: {avg_val_loss:.6f} | R²: {current_r2:.4f} | "
#                            f"Best R²: {best_r2:.4f}")
            
#             if patience_counter >= patience:
#                 logger.info(f"Early stopping at epoch {epoch+1}")
#                 break
        
#         # Load best model
#         if best_model_state:
#             self.model.load_state_dict(best_model_state)
#             logger.info("Loaded best model state")
        
#         # Final evaluation
#         self.model.eval()
#         val_preds = []
#         val_actuals = []
        
#         with torch.no_grad():
#             for batch_X, batch_y in val_loader:
#                 batch_X = batch_X.to(self.device)
#                 batch_y = batch_y.to(self.device)
#                 outputs = self.model(batch_X)
#                 val_preds.extend(outputs.cpu().numpy().flatten())
#                 val_actuals.extend(batch_y.cpu().numpy().flatten())
        
#         val_preds = np.array(val_preds)
#         val_actuals = np.array(val_actuals)
        
#         # Calculate metrics
#         metrics = self.performance_analyzer.calculate_metrics(val_actuals, val_preds)
        
#         # Prepare full metrics
#         full_metrics = {
#             **metrics,
#             'best_val_loss': float(best_val_loss),
#             'epochs_trained': epoch + 1,
#             'model_type': model_type,
#             'input_features': input_dim,
#             'seq_length': self.SEQ_LEN,
#             'pred_days': self.PRED_DAYS,
#             'timestamp': datetime.now().isoformat()
#         }
        
#         # Get paths
#         model_path, scaler_path, metrics_path, feature_path = self._get_paths(ticker)
        
#         # Save model and artifacts
#         try:
#             # Check if scaler and features exist BEFORE saving model
#             scaler_exists_before = os.path.exists(scaler_path)
#             feature_exists_before = os.path.exists(feature_path)
            
#             logger.info(f"[DEBUG] Files before model save - Scaler: {scaler_exists_before}, Features: {feature_exists_before}")
            
#             if scaler_exists_before and feature_exists_before:
#                 logger.info(f"[DEBUG] Scaler size: {os.path.getsize(scaler_path)}, Features size: {os.path.getsize(feature_path)}")
            
#             # Save model
#             torch.save(self.model.state_dict(), model_path)
#             logger.info(f"[OK] Saved model to {model_path} ({os.path.getsize(model_path)} bytes)")
            
#             # Save metrics
#             with open(metrics_path, 'wb') as f:
#                 joblib.dump(full_metrics, f, compress=3)
#             logger.info(f"[OK] Saved metrics to {metrics_path} ({os.path.getsize(metrics_path)} bytes)")
            
#             # Check if scaler and features still exist AFTER saving model
#             scaler_exists_after = os.path.exists(scaler_path)
#             feature_exists_after = os.path.exists(feature_path)
            
#             logger.info(f"[DEBUG] Files after model save - Scaler: {scaler_exists_after}, Features: {feature_exists_after}")
            
#             # Re-save scaler and features if they disappeared
#             if not scaler_exists_after or not feature_exists_after:
#                 logger.warning(f"[WARNING] Files disappeared! Re-saving scaler and features...")
#                 with open(scaler_path, 'wb') as f:
#                     joblib.dump(self.scaler, f, compress=3)
#                 with open(feature_path, 'wb') as f:
#                     joblib.dump(self.feature_cols, f, compress=3)
#                 logger.info(f"[OK] Re-saved scaler and features")
            
#             # Force sync
#             if hasattr(os, 'sync'):
#                 os.sync()
            
#             time.sleep(0.5)
            
#             # Final verification
#             verification = {
#                 'model': (model_path, os.path.exists(model_path)),
#                 'scaler': (scaler_path, os.path.exists(scaler_path)),
#                 'features': (feature_path, os.path.exists(feature_path)),
#                 'metrics': (metrics_path, os.path.exists(metrics_path))
#             }
            
#             saved_files = [name for name, (path, exists) in verification.items() if exists]
#             missing_files = [name for name, (path, exists) in verification.items() if not exists]
            
#             if missing_files:
#                 logger.error(f"[ERROR] Missing files after save: {missing_files}")
#                 for name, (path, exists) in verification.items():
#                     logger.error(f"  - {name}: {path} (exists: {exists})")
#                     if exists:
#                         logger.error(f"    Size: {os.path.getsize(path)} bytes")
#             else:
#                 logger.info(f"[OK] All artifacts verified:")
#                 for name, (path, exists) in verification.items():
#                     logger.info(f"  - {name}: {os.path.getsize(path)} bytes")
                
#         except Exception as e:
#             logger.error(f"[ERROR] Exception during save: {e}")
#             import traceback
#             logger.error(traceback.format_exc())
#             raise
        
#         # Generate visualizations
#         self.performance_analyzer.plot_results(train_losses, val_losses, val_actuals, val_preds, ticker)
        
#         logger.info("="*70)
#         logger.info(f"TRAINING COMPLETE: {ticker}")
#         logger.info(f"RMSE: {metrics['rmse']:.6f} | R²: {metrics['r2_score']:.4f} | "
#                    f"Dir Acc: {metrics['directional_accuracy']:.2f}%")
#         logger.info("="*70)
        
#         # Additional delay to ensure Windows file handles are released
#         time.sleep(1.0)
        
#         return {
#             "status": "success",
#             "ticker": ticker,
#             **full_metrics
#         }
    
#     def predict(self, ticker: str, capital: float = 100000, 
#                 risk_pct: float = 2.0, monte_carlo_samples: int = 30) -> Dict:
#         """Make prediction with uncertainty quantification"""
        
#         model_path, scaler_path, metrics_path, feature_path = self._get_paths(ticker)
        
#         # Verify all artifacts exist
#         required_files = [model_path, scaler_path, feature_path]
#         missing_files = [f for f in required_files if not os.path.exists(f)]
        
#         if missing_files:
#             return {
#                 "error": f"Missing artifacts for {ticker}. Train model first.",
#                 "missing_files": missing_files
#             }
        
#         # Prepare data
#         df = self.prepare_data(ticker)
#         if df is None:
#             return {"error": "Data preparation failed"}
        
#         # Load artifacts
#         try:
#             self.scaler = joblib.load(scaler_path)
#             self.feature_cols = joblib.load(feature_path)
#             metrics = joblib.load(metrics_path) if os.path.exists(metrics_path) else {}
#         except Exception as e:
#             return {"error": f"Error loading artifacts: {str(e)}"}
        
#         # Prepare features
#         data_values = df[self.feature_cols].values
#         scaled_data = self.scaler.transform(data_values)
        
#         if len(scaled_data) < self.SEQ_LEN:
#             return {"error": "Insufficient data for prediction"}
        
#         last_seq = scaled_data[-self.SEQ_LEN:]
#         last_seq_tensor = torch.FloatTensor(last_seq).unsqueeze(0).to(self.device)
        
#         # Load model
#         input_dim = last_seq.shape[1]
#         model_type = metrics.get('model_type', 'ensemble')
        
#         if model_type == 'lstm':
#             self.model = ImprovedLSTMModel(input_dim, hidden_dim=128, num_layers=3, dropout=0.25)
#         elif model_type == 'tcn':
#             self.model = TemporalConvNet(input_dim, hidden_dim=128, num_blocks=4, dropout=0.25)
#         elif model_type == 'transformer':
#             self.model = TransformerModel(input_dim, d_model=128, nhead=8, num_layers=3, dropout=0.25)
#         else:
#             self.model = AdvancedEnsemble(input_dim, hidden_dim=128)
        
#         self.model = self.model.to(self.device)
#         self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        
#         # Monte Carlo Dropout for uncertainty
#         predictions = []
#         self.model.train()  # Enable dropout
        
#         with torch.no_grad():
#             for _ in range(monte_carlo_samples):
#                 pred = self.model(last_seq_tensor).cpu().item()
#                 predictions.append(pred)
        
#         self.model.eval()
        
#         # Statistics
#         pred_mean = np.mean(predictions)
#         pred_std = np.std(predictions)
#         pred_lower = pred_mean - 1.96 * pred_std  # 95% CI
#         pred_upper = pred_mean + 1.96 * pred_std
        
#         # Inverse transform
#         dummy = np.zeros((1, len(self.feature_cols)))
#         target_idx = 0  # close is first
        
#         dummy[0, target_idx] = pred_mean
#         pred_price = self.scaler.inverse_transform(dummy)[0, target_idx]
        
#         dummy[0, target_idx] = pred_lower
#         pred_price_lower = self.scaler.inverse_transform(dummy)[0, target_idx]
        
#         dummy[0, target_idx] = pred_upper
#         pred_price_upper = self.scaler.inverse_transform(dummy)[0, target_idx]
        
#         # Current market data
#         current_price = df['close'].iloc[-1]
#         atr = df['atr_14'].iloc[-1] if 'atr_14' in df.columns else (current_price * 0.02)
#         rsi = df['rsi_14'].iloc[-1] if 'rsi_14' in df.columns else 50
#         volume_ratio = df['volume_ratio'].iloc[-1] if 'volume_ratio' in df.columns else 1.0
        
#         # Risk management
#         stop_loss = current_price - (2.5 * atr)
#         target_price = pred_price
        
#         risk_per_share = max(current_price - stop_loss, 0.01)
#         reward_per_share = target_price - current_price
#         rr_ratio = reward_per_share / risk_per_share if risk_per_share > 0 else 0
        
#         predicted_return = ((pred_price - current_price) / current_price) * 100
        
#         # Position sizing
#         max_loss = capital * (risk_pct / 100)
#         qty = int(max_loss / risk_per_share) if risk_per_share > 0 else 0
        
#         # Uncertainty score
#         uncertainty = pred_std / abs(pred_mean) if pred_mean != 0 else 1.0
        
#         # Signal generation
#         signal = "HOLD"
#         confidence = "LOW"
        
#         if predicted_return > 4 and rr_ratio > 2.5 and uncertainty < 0.1:
#             signal = "STRONG BUY"
#             confidence = "HIGH"
#         elif predicted_return > 2.5 and rr_ratio > 2.0 and uncertainty < 0.15:
#             signal = "BUY"
#             confidence = "HIGH"
#         elif predicted_return > 1.5 and rr_ratio > 1.5 and uncertainty < 0.2:
#             signal = "BUY"
#             confidence = "MEDIUM"
#         elif predicted_return < -4 and uncertainty < 0.1:
#             signal = "STRONG SELL"
#             confidence = "HIGH"
#         elif predicted_return < -2.5 and uncertainty < 0.15:
#             signal = "SELL"
#             confidence = "HIGH"
#         elif predicted_return < -1.5 and uncertainty < 0.2:
#             signal = "SELL"
#             confidence = "MEDIUM"
        
#         # Adjust signal based on model performance
#         model_r2 = metrics.get('r2_score', 0)
#         if model_r2 < 0.3:
#             confidence = "LOW"
        
#         return {
#             "ticker": ticker,
#             "timestamp": datetime.now().isoformat(),
#             "current_price": round(current_price, 2),
#             "predicted_price_5d": round(pred_price, 2),
#             "predicted_return_pct": round(predicted_return, 2),
#             "confidence_interval": {
#                 "lower": round(pred_price_lower, 2),
#                 "upper": round(pred_price_upper, 2),
#                 "width_pct": round(((pred_price_upper - pred_price_lower) / current_price) * 100, 2)
#             },
#             "signal": signal,
#             "prediction_confidence": confidence,
#             "uncertainty_score": round(uncertainty, 4),
#             "risk_management": {
#                 "stop_loss": round(stop_loss, 2),
#                 "target_price": round(target_price, 2),
#                 "risk_reward_ratio": round(rr_ratio, 2),
#                 "risk_per_share": round(risk_per_share, 2)
#             },
#             "position_sizing": {
#                 "suggested_quantity": qty,
#                 "trade_value": round(qty * current_price, 2),
#                 "max_loss_amount": round(max_loss, 2)
#             },
#             "technical_indicators": {
#                 "atr_14": round(atr, 2),
#                 "rsi_14": round(rsi, 2),
#                 "volume_ratio": round(volume_ratio, 2)
#             },
#             "model_performance": {
#                 "rmse": round(metrics.get('rmse', 0), 6),
#                 "r2_score": round(metrics.get('r2_score', 0), 4),
#                 "directional_accuracy": round(metrics.get('directional_accuracy', 0), 2),
#                 "mape": round(metrics.get('mape', 0), 2)
#             }
#         }
    
#     def batch_train_nifty500(self, model_type: str = 'ensemble', 
#                              max_stocks: int = None, epochs: int = 150) -> Dict:
#         """Batch train NIFTY 500 stocks"""
        
#         # Get tickers
#         query = text("""
#             SELECT ticker, COUNT(*) as cnt 
#             FROM nse_stocks 
#             GROUP BY ticker 
#             HAVING COUNT(*) >= :min_points
#             ORDER BY ticker
#         """)
        
#         try:
#             with self.engine.connect() as conn:
#                 result = conn.execute(query, {'min_points': self.MIN_DATA_POINTS})
#                 tickers = [row[0] for row in result]
#         except Exception as e:
#             logger.error(f"Error fetching tickers: {e}")
#             return {"status": "error", "message": str(e)}
        
#         if max_stocks:
#             tickers = tickers[:max_stocks]
        
#         logger.info("="*70)
#         logger.info(f"BATCH TRAINING: {len(tickers)} STOCKS")
#         logger.info("="*70)
        
#         results = {
#             "success": [],
#             "failed": [],
#             "metrics_summary": []
#         }
        
#         for ticker in tqdm(tickers, desc="Training Progress"):
#             try:
#                 result = self.train(
#                     ticker=ticker,
#                     force_retrain=False,
#                     model_type=model_type,
#                     epochs=epochs
#                 )
                
#                 if result['status'] == 'success':
#                     results['success'].append(ticker)
#                     results['metrics_summary'].append({
#                         'ticker': ticker,
#                         'rmse': result['rmse'],
#                         'r2_score': result['r2_score'],
#                         'directional_accuracy': result['directional_accuracy'],
#                         'mape': result['mape']
#                     })
#                 else:
#                     results['failed'].append(ticker)
                    
#             except Exception as e:
#                 logger.error(f"Failed {ticker}: {e}")
#                 results['failed'].append(ticker)
            
#             # Small delay between stocks
#             time.sleep(0.2)
        
#         # Generate summary
#         if results['metrics_summary']:
#             df_metrics = pd.DataFrame(results['metrics_summary'])
            
#             summary = f"""
# {'='*70}
# BATCH TRAINING SUMMARY
# {'='*70}
# Total: {len(results['success']) + len(results['failed'])}
# Success: {len(results['success'])}
# Failed: {len(results['failed'])}

# AVERAGE METRICS:
# RMSE: {df_metrics['rmse'].mean():.6f}
# R² Score: {df_metrics['r2_score'].mean():.4f}
# Dir Acc: {df_metrics['directional_accuracy'].mean():.2f}%
# MAPE: {df_metrics['mape'].mean():.2f}%

# TOP 10 BY R²:
# {df_metrics.nlargest(10, 'r2_score')[['ticker', 'r2_score', 'directional_accuracy']].to_string(index=False)}
# {'='*70}
# """
#             print(summary)
            
#             with open(f"{METRICS_DIR}/batch_summary.txt", 'w', encoding='utf-8') as f:
#                 f.write(summary)
            
#             df_metrics.to_csv(f"{METRICS_DIR}/batch_metrics.csv", index=False)
        
#         logger.info("="*70)
#         logger.info(f"BATCH TRAINING COMPLETE")
#         logger.info(f"Success: {len(results['success']) + len(results['failed'])} | Failed: {len(results['failed'])}")
#         logger.info("="*70)
        
#         return results


# # ==================== MAIN ====================

# if __name__ == "__main__":
#     predictor = ProductionStockPredictor()
    
#     # Example 1: Train single stock
#     print("\n" + "="*70)
#     print("EXAMPLE 1: TRAINING")
#     print("="*70)
    
#     result = predictor.train(
#         ticker="TATAPOWER",
#         force_retrain=True,
#         model_type='ensemble',  # 'lstm', 'tcn', 'transformer', or 'ensemble'
#         epochs=150
#     )
#     print(json.dumps(result, indent=2))
    
#     # Longer delay to ensure all files are saved
#     print("\nWaiting for file system sync...")
#     time.sleep(2.0)
    
#     # Example 2: Make prediction
#     if result['status'] == 'success':
#         print("\n" + "="*70)
#         print("EXAMPLE 2: PREDICTION")
#         print("="*70)
        
#         prediction = predictor.predict(
#             ticker="TATAPOWER",
#             capital=100000,
#             risk_pct=2.0
#         )
#         print(json.dumps(prediction, indent=2))
    
#     # Example 3: Batch training (uncomment to run)
#     # print("\n" + "="*70)
#     # print("EXAMPLE 3: BATCH TRAINING")
#     # print("="*70)
#     # batch_results = predictor.batch_train_nifty500(model_type='ensemble', max_stocks=10, epochs=100)





"""
===================================================================
UNIFIED PRODUCTION-READY STOCK PREDICTOR - OPTIMIZED VERSION
===================================================================

Complete end-to-end ML prediction system in ONE file:
- Feature engineering with database integration
- Multi-task deep learning model
- Training pipeline with monitoring
- Prediction API with risk management
- Performance visualization

OPTIMIZATIONS:
- Fixed BCELoss autocast error (BCEWithLogitsLoss)
- Added mixed precision training with GradScaler
- Parallel data loading with num_workers
- Gradient accumulation for larger effective batch size
- Optimized data loading pipeline

Author: GenAI Stock Intelligence System
Version: 2.2.0 (OPTIMIZED & FIXED)
Date: 2026-02-13

Usage:
    python MLPredictor.py train
    python MLPredictor.py predict RELIANCE
    python MLPredictor.py batch-predict
===================================================================
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.cuda.amp import autocast, GradScaler
import numpy as np
import pandas as pd
import os
import joblib
import logging
import sys
import argparse
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, accuracy_score
from torch.utils.data import DataLoader, Dataset
from sqlalchemy import create_engine, text
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import warnings
from tqdm import tqdm
import matplotlib.pyplot as plt
import seaborn as sns
import json
import time
import threading
from collections import defaultdict, deque

warnings.filterwarnings('ignore')

# ==================== CONFIGURATION ====================

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('unified_predictor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Directories
MODEL_DIR = "unified_models"
METRICS_DIR = "unified_metrics"
PLOTS_DIR = "unified_plots"

for directory in [MODEL_DIR, METRICS_DIR, PLOTS_DIR]:
    os.makedirs(directory, exist_ok=True)

# Database
DB_URL = "postgresql://postgres:Taran%4017@localhost:5432/StockDB"

# Model hyperparameters - OPTIMIZED FOR SPEED
CONFIG = {
    'seq_len': 40,
    'pred_days': 5,
    'hidden_dim': 128,
    'dropout': 0.2,
    'batch_size': 256,  # Increased for better GPU utilization
    'learning_rate': 0.001,
    'epochs': 100,
    'patience': 15,
    'num_workers': 4,  # Parallel data loading
    'gradient_accumulation_steps': 1,  # Can increase for larger effective batch size
}


# ==================== FEATURE ENGINEERING ====================

class QuickFeatureEngineer:
    """
    Lightweight feature engineering
    Creates essential features without heavy dependencies
    """
    
    @staticmethod
    def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators and features"""
        df = df.copy()
        df = df.sort_values('date').reset_index(drop=True)
        
        # Price features
        for period in [5, 10, 20, 50]:
            df[f'sma_{period}'] = df['close'].rolling(period).mean()
            df[f'ema_{period}'] = df['close'].ewm(span=period).mean()
        
        # Momentum
        for period in [1, 5, 10, 20]:
            df[f'return_{period}d'] = df['close'].pct_change(period)
        
        # Volatility
        for period in [10, 20]:
            df[f'volatility_{period}'] = df['close'].pct_change().rolling(period).std()
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / (loss + 1e-8)
        df['rsi_14'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema_12 = df['close'].ewm(span=12).mean()
        ema_26 = df['close'].ewm(span=26).mean()
        df['macd'] = ema_12 - ema_26
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands
        sma_20 = df['close'].rolling(20).mean()
        std_20 = df['close'].rolling(20).std()
        df['bb_upper'] = sma_20 + (2 * std_20)
        df['bb_lower'] = sma_20 - (2 * std_20)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / (sma_20 + 1e-8)
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'] + 1e-8)
        
        # Volume features
        df['volume_sma_20'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / (df['volume_sma_20'] + 1)
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['atr_14'] = true_range.rolling(14).mean()
        
        # Price patterns
        df['body_size'] = np.abs(df['close'] - df['open']) / (df['close'] + 1e-8)
        df['upper_wick'] = df['high'] - df[['open', 'close']].max(axis=1)
        df['lower_wick'] = df[['open', 'close']].min(axis=1) - df['low']
        
        # Price position
        df['high_20'] = df['high'].rolling(20).max()
        df['low_20'] = df['low'].rolling(20).min()
        df['price_position'] = (df['close'] - df['low_20']) / (df['high_20'] - df['low_20'] + 1e-8)
        
        # Trend
        df['trend_20'] = np.where(df['close'] > df['sma_20'], 1, 0)
        
        # Clean up - AGGRESSIVE CLEANING
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.ffill().bfill().fillna(0.0)
        
        return df


# ==================== NEURAL NETWORK ARCHITECTURE - FIXED ====================

class StockPredictorModel(nn.Module):
    """
    Multi-task deep learning model for stock prediction
    
    FIXED: Removed sigmoid from direction_head to use BCEWithLogitsLoss
    """
    
    def __init__(self, input_dim, hidden_dim=128, dropout=0.2):
        super().__init__()
        
        # Input processing
        self.input_norm = nn.LayerNorm(input_dim)
        self.input_proj = nn.Linear(input_dim, hidden_dim)
        
        # Bi-LSTM
        self.lstm = nn.LSTM(
            hidden_dim,
            hidden_dim // 2,
            num_layers=2,
            batch_first=True,
            dropout=dropout,
            bidirectional=True
        )
        
        # Self-attention
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_dim,
            num_heads=4,
            dropout=dropout,
            batch_first=True
        )
        
        # Normalization
        self.norm1 = nn.LayerNorm(hidden_dim)
        self.norm2 = nn.LayerNorm(hidden_dim)
        
        # Feed-forward
        self.ff = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, hidden_dim)
        )
        
        # Task-specific heads
        self.price_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, 1)
        )
        
        # FIXED: Removed Sigmoid - will use BCEWithLogitsLoss
        self.direction_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, 1)
            # NO SIGMOID HERE - BCEWithLogitsLoss expects raw logits
        )
        
        self.volatility_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, 1),
            nn.Softplus()
        )
        
        self.confidence_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, 1),
            nn.Sigmoid()
        )
    
    def forward(self, x):
        # Normalize and project
        x = self.input_norm(x)
        x = F.gelu(self.input_proj(x))
        
        # LSTM
        lstm_out, _ = self.lstm(x)
        
        # Self-attention with residual
        attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)
        x = self.norm1(lstm_out + attn_out)
        
        # Feed-forward with residual
        ff_out = self.ff(x)
        x = self.norm2(x + ff_out)
        
        # Use last timestep
        x = x[:, -1, :]
        
        # Multi-task predictions
        return {
            'price': self.price_head(x),
            'direction': self.direction_head(x),  # Raw logits
            'volatility': self.volatility_head(x),
            'confidence': self.confidence_head(x)
        }


# ==================== DATASET ====================

class StockDataset(Dataset):
    """PyTorch dataset for stock sequences — legacy wrapper for pre-computed arrays."""
    
    def __init__(self, features, targets):
        # Convert to float32 explicitly to save RAM
        self.features = torch.FloatTensor(features)
        self.targets = {
            k: torch.FloatTensor(v).unsqueeze(-1) if v.ndim == 1 else torch.FloatTensor(v) 
            for k, v in targets.items()
        }
    
    def __len__(self):
        return len(self.features)
    
    def __getitem__(self, idx):
        return self.features[idx], {k: v[idx] for k, v in self.targets.items()}


class StreamingStockDataset(Dataset):
    """
    Memory-efficient dataset that creates sequences ON-THE-FLY.
    
    Instead of materializing all 2.2M sequences (~22 GB), this dataset:
    - Holds only the per-ticker numpy arrays in memory (~600 MB total)
    - Builds an index of (ticker_idx, row_offset) tuples (~17 MB)
    - Creates each 40-step window + targets in __getitem__
    
    This enables training on all 2078 stocks without OOM.
    """
    
    def __init__(self, ticker_arrays, index, feature_scaler=None, target_scalers=None):
        """
        Args:
            ticker_arrays: list of (features_array, close_array) per ticker
            index: list of (ticker_idx, start_row) tuples
            feature_scaler: fitted RobustScaler for features (or None)
            target_scalers: dict of fitted scalers for targets (or None)
        """
        self.ticker_arrays = ticker_arrays
        self.index = index
        self.feature_scaler = feature_scaler
        self.target_scalers = target_scalers or {}
        self.seq_len = CONFIG['seq_len']
        self.pred_days = CONFIG['pred_days']
    
    def __len__(self):
        return len(self.index)
    
    def __getitem__(self, idx):
        ticker_idx, start_row = self.index[idx]
        features_arr, close_arr = self.ticker_arrays[ticker_idx]
        
        # Extract sequence window
        seq = features_arr[start_row:start_row + self.seq_len].copy()
        
        # Scale features on-the-fly if scaler is available
        if self.feature_scaler is not None:
            original_shape = seq.shape
            seq = self.feature_scaler.transform(seq.reshape(-1, original_shape[-1]))
            seq = seq.reshape(original_shape)
        
        seq = np.clip(np.nan_to_num(seq, nan=0.0, posinf=0.0, neginf=0.0), -10, 10)
        
        # Compute targets
        current_price = float(close_arr[start_row + self.seq_len - 1])
        future_price = float(close_arr[start_row + self.seq_len + self.pred_days - 1])
        
        price_change = future_price - current_price
        direction = 1.0 if future_price > current_price else 0.0
        
        # Volatility from future returns
        future_closes = close_arr[start_row + self.seq_len:start_row + self.seq_len + self.pred_days]
        if len(future_closes) > 1:
            returns = np.diff(future_closes) / (future_closes[:-1] + 1e-8)
            volatility = float(np.std(returns)) if len(returns) > 0 else 0.0
        else:
            volatility = 0.0
        
        # Scale targets on-the-fly
        if 'price' in self.target_scalers:
            price_change = float(self.target_scalers['price'].transform([[price_change]])[0, 0])
        if 'volatility' in self.target_scalers:
            volatility = float(self.target_scalers['volatility'].transform([[volatility]])[0, 0])
        
        features_tensor = torch.FloatTensor(seq.astype(np.float32))
        targets = {
            'price': torch.FloatTensor([price_change]),
            'direction': torch.FloatTensor([direction]),
            'volatility': torch.FloatTensor([volatility]),
        }
        
        return features_tensor, targets


# ==================== RL FEEDBACK BUFFER ====================

class RLFeedbackBuffer:
    """
    Circular buffer storing (prediction, actual_outcome) pairs for
    online reinforcement learning.
    Uses REINFORCE policy gradient with tiny learning rate.
    """

    def __init__(self, max_size: int = 1000, update_every: int = 5, rl_lr: float = 1e-5):
        self.buffer = deque(maxlen=max_size)
        self.update_every = update_every
        self.rl_lr = rl_lr
        self.total_updates = 0
        self.total_reward = 0.0
        self.lock = threading.Lock()
        self._pending_predictions: Dict[str, Dict] = {}  # ticker+date → prediction

    def record_prediction(self, ticker: str, predicted_direction: float,
                          predicted_price: float, current_price: float,
                          model_output: Dict[str, float]):
        """Record a prediction for later comparison with actual."""
        key = f"{ticker}_{datetime.now().strftime('%Y%m%d')}"
        with self.lock:
            self._pending_predictions[key] = {
                'ticker': ticker,
                'timestamp': datetime.now(),
                'predicted_direction': predicted_direction,
                'predicted_price': predicted_price,
                'current_price': current_price,
                'model_output': model_output,
            }

    def record_actual(self, ticker: str, date_str: str, actual_price: float):
        """Record actual price and compute reward."""
        key = f"{ticker}_{date_str}"
        with self.lock:
            if key not in self._pending_predictions:
                return None
            pred = self._pending_predictions.pop(key)

        actual_direction = 1.0 if actual_price > pred['current_price'] else 0.0
        predicted_dir = 1.0 if pred['predicted_direction'] > 0.5 else 0.0

        # Reward: +1 for correct direction, -1 for wrong, scaled by magnitude
        direction_correct = float(actual_direction == predicted_dir)
        price_error = abs(actual_price - pred['predicted_price']) / max(pred['current_price'], 1)
        reward = (direction_correct * 2 - 1) * (1 - min(price_error, 1.0))

        sample = {
            'ticker': ticker,
            'reward': reward,
            'direction_correct': direction_correct,
            'model_output': pred['model_output'],
            'price_error': price_error,
        }

        with self.lock:
            self.buffer.append(sample)
            self.total_reward += reward

        return sample

    def should_update(self) -> bool:
        return len(self.buffer) >= self.update_every

    def get_batch(self) -> List[Dict]:
        with self.lock:
            batch = list(self.buffer)[-self.update_every:]
        return batch

    def get_stats(self) -> Dict:
        with self.lock:
            n = len(self.buffer)
            if n == 0:
                return {'samples': 0, 'updates': 0, 'avg_reward': 0}
            rewards = [s['reward'] for s in self.buffer]
            accuracies = [s['direction_correct'] for s in self.buffer]
        return {
            'samples': n,
            'updates': self.total_updates,
            'avg_reward': round(np.mean(rewards), 4),
            'direction_accuracy': round(np.mean(accuracies) * 100, 1),
            'total_reward': round(self.total_reward, 4),
            'pending_predictions': len(self._pending_predictions),
        }


# ==================== PREDICTION TRACKER ====================

class PredictionTracker:
    """
    Tracks prediction history and rolling accuracy per ticker.
    Persists to a JSON file for survival across restarts.
    """

    def __init__(self, filepath: str = f"{METRICS_DIR}/prediction_history.json"):
        self.filepath = filepath
        self.history: Dict[str, List[Dict]] = {}  # ticker → list of predictions
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, 'r') as f:
                    self.history = json.load(f)
        except Exception:
            self.history = {}

    def _save(self):
        try:
            with open(self.filepath, 'w') as f:
                json.dump(self.history, f, indent=2, default=str)
        except Exception as e:
            logger.debug(f"Failed to save prediction history: {e}")

    def record(self, ticker: str, prediction: Dict):
        if ticker not in self.history:
            self.history[ticker] = []
        entry = {
            'timestamp': datetime.now().isoformat(),
            'predicted_price': prediction.get('price_analysis', {}).get('predicted_price_5d'),
            'current_price': prediction.get('price_analysis', {}).get('current_price'),
            'signal': prediction.get('recommendation', {}).get('signal'),
            'confidence': prediction.get('recommendation', {}).get('confidence_score'),
            'actual_price': None,  # Filled later
            'accurate': None,
        }
        self.history[ticker].append(entry)
        # Keep last 100 predictions per ticker
        self.history[ticker] = self.history[ticker][-100:]
        self._save()

    def get_accuracy(self, ticker: str, days: int = 30) -> Optional[float]:
        if ticker not in self.history or len(self.history[ticker]) < 5:
            return None
        recent = self.history[ticker][-days:]
        verified = [p for p in recent if p.get('accurate') is not None]
        if not verified:
            return None
        return sum(1 for p in verified if p['accurate']) / len(verified)


# ==================== MAIN PREDICTOR CLASS ====================

class UnifiedStockPredictor:
    """
    Complete prediction system with training, prediction, and monitoring
    
    OPTIMIZED VERSION with:
    - Mixed precision training (AMP)
    - Parallel data loading
    - Fixed BCEWithLogitsLoss
    """
    
    def __init__(self, db_url: str = DB_URL):
        self.db_url = db_url
        self.engine = create_engine(db_url, pool_pre_ping=True)
        self.model = None
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.feature_scaler = None
        self.target_scalers = {}
        self.feature_cols = None
        self.metrics_history = defaultdict(list)
        self.rl_buffer = RLFeedbackBuffer()
        self.prediction_tracker = PredictionTracker()
        
        logger.info(f"🚀 Initialized on device: {self.device}")
        logger.info(f"   CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            logger.info(f"   GPU: {torch.cuda.get_device_name(0)}")
    
    def _get_paths(self):
        """Get file paths for model artifacts"""
        return (
            f"{MODEL_DIR}/unified_model.pth",
            f"{MODEL_DIR}/feature_scaler.pkl",
            f"{MODEL_DIR}/target_scalers.pkl",
            f"{MODEL_DIR}/feature_cols.pkl",
            f"{MODEL_DIR}/metrics_history.pkl"
        )
    
    def load_or_engineer_features(self, max_tickers: Optional[int] = None) -> pd.DataFrame:
        """
        Load data from database and engineer features
        """
        logger.info("="*70)
        logger.info("📊 LOADING DATA FROM DATABASE")
        logger.info("="*70)
        
        # Query to get all data
        query = text("""
            SELECT ticker, date, open, high, low, close, volume, adj_close
            FROM nse_stocks
            ORDER BY ticker ASC, date ASC
        """)
        
        try:
            df = pd.read_sql(query, self.engine)
            logger.info(f"   Loaded {len(df):,} rows from database")
        except Exception as e:
            logger.error(f"Database error: {e}")
            raise
        
        if df.empty:
            raise ValueError("No data found in database!")
        
        # Limit tickers if specified
        if max_tickers:
            unique_tickers = df['ticker'].unique()[:max_tickers]
            df = df[df['ticker'].isin(unique_tickers)]
            logger.info(f"   Limited to {max_tickers} tickers")
        
        logger.info("="*70)
        logger.info("⚙️ ENGINEERING FEATURES")
        logger.info("="*70)
        
        # Engineer features per ticker
        all_dfs = []
        tickers = df['ticker'].unique()
        
        for ticker in tqdm(tickers, desc="Engineering Features"):
            ticker_df = df[df['ticker'] == ticker].copy()
            
            if len(ticker_df) < 100:  # Skip tickers with insufficient data
                continue
            
            # Add features
            ticker_df = QuickFeatureEngineer.engineer_features(ticker_df)
            ticker_df['ticker'] = ticker
            all_dfs.append(ticker_df)
        
        result_df = pd.concat(all_dfs, ignore_index=True)
        logger.info(f"✅ Engineered features for {len(all_dfs)} tickers")
        logger.info(f"   Total rows: {len(result_df):,}")
        logger.info(f"   Features: {len(result_df.columns)}")
        
        return result_df
    
    def train(self, max_tickers=None, epochs=None, batch_size=None, learning_rate=None):
        """
        Train the prediction model — OPTIMIZED VERSION
        
        IMPROVEMENTS:
        - Mixed precision training with GradScaler
        - Parallel data loading with multiple workers
        - Fixed BCEWithLogitsLoss for direction prediction
        - Better progress tracking
        """
        logger.info("="*70)
        logger.info("🎯 TRAINING STOCK PREDICTOR - OPTIMIZED")
        logger.info("="*70)
        
        # Use config defaults
        epochs = epochs or CONFIG['epochs']
        batch_size = batch_size or CONFIG['batch_size']
        learning_rate = learning_rate or CONFIG['learning_rate']
        num_workers = CONFIG['num_workers']
        
        # Load features
        df = self.load_or_engineer_features(max_tickers=max_tickers)
        
        # ================================================================
        # STEP 1: Build per-ticker arrays and sequence index (lightweight)
        # ================================================================
        logger.info("="*70)
        logger.info("🔧 BUILDING SEQUENCE INDEX (memory-efficient)")
        logger.info("="*70)
        
        seq_len = CONFIG['seq_len']
        pred_days = CONFIG['pred_days']
        
        # Preserve ticker info before numeric filtering
        if 'ticker' in df.columns:
            ticker_series = df['ticker'].copy()
            tickers = ticker_series.unique()
        else:
            ticker_series = None
            tickers = np.array(['__all__'])
        
        # Keep only numeric columns
        df_numeric = df.select_dtypes(include=[np.number]).copy()
        if ticker_series is not None:
            df_numeric['ticker'] = ticker_series.values
        
        # Select feature columns
        exclude_cols = ['ticker'] + [c for c in df_numeric.columns if c.startswith('target_')]
        if 'close' not in df_numeric.columns:
            raise ValueError("'close' column not found!")
        
        feature_cols = [c for c in df_numeric.columns if c not in exclude_cols and pd.api.types.is_numeric_dtype(df_numeric[c])]
        if self.feature_cols is None:
            self.feature_cols = feature_cols
        
        n_features = len(feature_cols)
        logger.info(f"   Features: {n_features}")
        logger.info(f"   Tickers: {len(tickers)}")
        
        # Build per-ticker arrays and index
        ticker_arrays = []  # list of (features_ndarray, close_ndarray)
        all_index = []      # list of (ticker_idx, start_row)
        
        for ticker in tqdm(tickers, desc="Indexing Tickers"):
            try:
                if 'ticker' in df_numeric.columns:
                    ticker_df = df_numeric[df_numeric['ticker'] == ticker]
                else:
                    ticker_df = df_numeric
                
                if len(ticker_df) < seq_len + pred_days + 10:
                    continue
                
                available_cols = [c for c in feature_cols if c in ticker_df.columns]
                if len(available_cols) == 0:
                    continue
                
                feat_arr = ticker_df[available_cols].values.astype(np.float32)
                feat_arr = np.nan_to_num(feat_arr, nan=0.0, posinf=0.0, neginf=0.0)
                close_arr = ticker_df['close'].values.astype(np.float32)
                
                ticker_idx = len(ticker_arrays)
                ticker_arrays.append((feat_arr, close_arr))
                
                # Each valid starting position becomes an index entry
                n_valid = len(feat_arr) - seq_len - pred_days
                for i in range(n_valid):
                    all_index.append((ticker_idx, i))
                    
            except Exception as e:
                logger.warning(f"Error indexing {ticker}: {e}")
                continue
        
        if not all_index:
            raise ValueError("No valid sequences found!")
        
        total_sequences = len(all_index)
        logger.info(f"✅ Indexed {total_sequences:,} sequences across {len(ticker_arrays)} tickers")
        logger.info(f"   Memory: ~{sum(a[0].nbytes + a[1].nbytes for a in ticker_arrays) / 1e6:.0f} MB")
        
        # ================================================================
        # STEP 2: Train/validation split (time-based per ticker)
        # ================================================================
        split_ratio = 0.85
        split_idx = int(total_sequences * split_ratio)
        train_index = all_index[:split_idx]
        val_index = all_index[split_idx:]
        
        logger.info(f"   Train: {len(train_index):,} | Val: {len(val_index):,}")
        
        # ================================================================
        # STEP 3: Fit scalers on a SAMPLE (not the full dataset)
        # ================================================================
        logger.info("Fitting scalers on sample...")
        
        sample_size = min(50000, len(train_index))
        sample_indices = np.random.choice(len(train_index), sample_size, replace=False)
        
        # Feature scaler: sample sequences, reshape to (sample_size * seq_len, n_features)
        sample_features = []
        sample_prices = []
        sample_vols = []
        
        for si in sample_indices:
            t_idx, s_row = train_index[si]
            feat_arr, close_arr = ticker_arrays[t_idx]
            
            seq = feat_arr[s_row:s_row + seq_len]
            sample_features.append(seq.reshape(-1, n_features))  # (seq_len, n_features)
            
            cur_price = float(close_arr[s_row + seq_len - 1])
            fut_price = float(close_arr[s_row + seq_len + pred_days - 1])
            sample_prices.append(fut_price - cur_price)
            
            future_closes = close_arr[s_row + seq_len:s_row + seq_len + pred_days]
            if len(future_closes) > 1:
                rets = np.diff(future_closes) / (future_closes[:-1] + 1e-8)
                sample_vols.append(float(np.std(rets)))
            else:
                sample_vols.append(0.0)
        
        sample_feat_flat = np.vstack(sample_features).astype(np.float32)
        sample_feat_flat = np.clip(np.nan_to_num(sample_feat_flat), -1e9, 1e9)
        
        self.feature_scaler = RobustScaler()
        self.feature_scaler.fit(sample_feat_flat)
        
        # Target scalers
        self.target_scalers = {}
        for key, values in [('price', sample_prices), ('volatility', sample_vols)]:
            scaler = RobustScaler()
            arr = np.array(values, dtype=np.float32).reshape(-1, 1)
            arr = np.clip(np.nan_to_num(arr), -1e9, 1e9)
            scaler.fit(arr)
            self.target_scalers[key] = scaler
        
        del sample_features, sample_feat_flat, sample_prices, sample_vols
        
        logger.info("✅ Scalers fitted on sample")
        
        # ================================================================
        # STEP 4: Create streaming datasets
        # ================================================================
        train_dataset = StreamingStockDataset(
            ticker_arrays, train_index,
            feature_scaler=self.feature_scaler,
            target_scalers=self.target_scalers,
        )
        val_dataset = StreamingStockDataset(
            ticker_arrays, val_index,
            feature_scaler=self.feature_scaler,
            target_scalers=self.target_scalers,
        )
        
        # OPTIMIZED: Parallel data loading with num_workers
        train_loader = DataLoader(
            train_dataset, 
            batch_size=batch_size, 
            shuffle=True,
            num_workers=num_workers,  # PARALLEL LOADING
            pin_memory=True,
            persistent_workers=True if num_workers > 0 else False,
        )
        val_loader = DataLoader(
            val_dataset, 
            batch_size=batch_size, 
            shuffle=False,
            num_workers=num_workers,  # PARALLEL LOADING
            pin_memory=True,
            persistent_workers=True if num_workers > 0 else False,
        )
        
        logger.info(f"   Train batches: {len(train_loader):,} | Val batches: {len(val_loader):,}")
        
        # ================================================================
        # STEP 5: Initialize model and train
        # ================================================================
        logger.info("="*70)
        logger.info("🚀 INITIALIZING MODEL")
        logger.info("="*70)
        
        input_dim = n_features
        self.model = StockPredictorModel(
            input_dim, 
            hidden_dim=CONFIG['hidden_dim'], 
            dropout=CONFIG['dropout']
        )
        self.model = self.model.to(self.device)
        
        total_params = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        logger.info(f"🧠 Model parameters: {total_params:,}")
        
        # Optimizer & scheduler
        optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=learning_rate,
            weight_decay=1e-4
        )
        
        lr_scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', factor=0.5, patience=5, verbose=True
        )
        
        # OPTIMIZED: Mixed precision training
        scaler = GradScaler() if self.device == 'cuda' else None
        
        # Loss functions - FIXED: Use BCEWithLogitsLoss
        mse_loss = nn.MSELoss()
        bce_loss = nn.BCEWithLogitsLoss()  # FIXED: Safe for autocast
        
        # Training loop
        best_score = float('inf')
        patience = CONFIG['patience']
        patience_counter = 0
        
        logger.info("="*70)
        logger.info(f"🚀 Starting training: {epochs} epochs")
        logger.info(f"   Batch size: {batch_size} | Workers: {num_workers}")
        logger.info(f"   Mixed Precision: {scaler is not None}")
        logger.info("="*70)
        
        for epoch in range(epochs):
            # Training phase
            self.model.train()
            train_loss = 0
            
            pbar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{epochs}")
            for features, targets in pbar:
                features = features.to(self.device)
                targets = {k: v.to(self.device) for k, v in targets.items()}
                
                optimizer.zero_grad()
                
                # OPTIMIZED: Mixed precision training
                if scaler:
                    with autocast():
                        preds = self.model(features)
                        
                        # Multi-task loss
                        loss_price = mse_loss(preds['price'], targets['price'])
                        loss_direction = bce_loss(preds['direction'], targets['direction'])
                        loss_volatility = mse_loss(preds['volatility'], targets['volatility'])
                        
                        total_loss = 2.0 * loss_price + 1.5 * loss_direction + 1.0 * loss_volatility
                    
                    scaler.scale(total_loss).backward()
                    scaler.unscale_(optimizer)
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    preds = self.model(features)
                    
                    # Multi-task loss
                    loss_price = mse_loss(preds['price'], targets['price'])
                    loss_direction = bce_loss(preds['direction'], targets['direction'])
                    loss_volatility = mse_loss(preds['volatility'], targets['volatility'])
                    
                    total_loss = 2.0 * loss_price + 1.5 * loss_direction + 1.0 * loss_volatility
                    
                    total_loss.backward()
                    torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
                    optimizer.step()
                
                train_loss += total_loss.item()
                pbar.set_postfix({'loss': f"{total_loss.item():.4f}"})
            
            train_loss /= len(train_loader)
            
            # Validation phase
            self.model.eval()
            val_loss = 0
            val_preds = defaultdict(list)
            val_actuals = defaultdict(list)
            
            with torch.no_grad():
                for features, targets in val_loader:
                    features = features.to(self.device)
                    targets = {k: v.to(self.device) for k, v in targets.items()}
                    
                    if scaler:
                        with autocast():
                            preds = self.model(features)
                            
                            loss_price = mse_loss(preds['price'], targets['price'])
                            loss_direction = bce_loss(preds['direction'], targets['direction'])
                            loss_volatility = mse_loss(preds['volatility'], targets['volatility'])
                            
                            total_loss = 2.0 * loss_price + 1.5 * loss_direction + 1.0 * loss_volatility
                    else:
                        preds = self.model(features)
                        
                        loss_price = mse_loss(preds['price'], targets['price'])
                        loss_direction = bce_loss(preds['direction'], targets['direction'])
                        loss_volatility = mse_loss(preds['volatility'], targets['volatility'])
                        
                        total_loss = 2.0 * loss_price + 1.5 * loss_direction + 1.0 * loss_volatility
                    
                    val_loss += total_loss.item()
                    
                    # Apply sigmoid to direction predictions for evaluation
                    preds_eval = preds.copy()
                    preds_eval['direction'] = torch.sigmoid(preds['direction'])
                    
                    for key in preds_eval:
                        val_preds[key].extend(preds_eval[key].cpu().numpy().flatten())
                    for key in targets:
                        val_actuals[key].extend(targets[key].cpu().numpy().flatten())
            
            val_loss /= len(val_loader)
            
            # Calculate metrics
            direction_preds = (np.array(val_preds['direction']) > 0.5).astype(int)
            direction_actuals = np.array(val_actuals['direction']).astype(int)
            direction_accuracy = accuracy_score(direction_actuals, direction_preds) * 100
            
            # Inverse transform for price metrics
            price_preds_orig = self.target_scalers['price'].inverse_transform(
                np.array(val_preds['price']).reshape(-1, 1)
            ).flatten()
            price_actuals_orig = self.target_scalers['price'].inverse_transform(
                np.array(val_actuals['price']).reshape(-1, 1)
            ).flatten()
            
            price_rmse = np.sqrt(mean_squared_error(price_actuals_orig, price_preds_orig))
            price_r2 = r2_score(price_actuals_orig, price_preds_orig)
            
            # Track metrics
            self.metrics_history['epoch'].append(epoch)
            self.metrics_history['train_loss'].append(train_loss)
            self.metrics_history['val_loss'].append(val_loss)
            self.metrics_history['direction_accuracy'].append(direction_accuracy)
            self.metrics_history['price_rmse'].append(price_rmse)
            self.metrics_history['price_r2'].append(price_r2)
            
            # Learning rate scheduling
            lr_scheduler.step(val_loss)
            
            # Early stopping
            if val_loss < best_score:
                best_score = val_loss
                patience_counter = 0
                model_path, _, _, _, _ = self._get_paths()
                torch.save({
                    'model_state_dict': self.model.state_dict(),
                    'optimizer_state_dict': optimizer.state_dict(),
                    'epoch': epoch,
                    'val_loss': val_loss,
                    'config': CONFIG
                }, model_path)
                logger.info(f"✅ Saved best model (val_loss: {val_loss:.4f})")
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    logger.info(f"⏰ Early stopping at epoch {epoch+1}")
                    break
            
            # Log epoch summary
            logger.info(
                f"Epoch {epoch+1}/{epochs} | "
                f"Train Loss: {train_loss:.4f} | "
                f"Val Loss: {val_loss:.4f} | "
                f"Dir Acc: {direction_accuracy:.1f}% | "
                f"Price RMSE: {price_rmse:.2f} | "
                f"Price R²: {price_r2:.4f}"
            )
        
        # Save final artifacts
        _, scaler_path, target_scalers_path, feature_cols_path, metrics_path = self._get_paths()
        joblib.dump(self.feature_scaler, scaler_path)
        joblib.dump(self.target_scalers, target_scalers_path)
        joblib.dump(self.feature_cols, feature_cols_path)
        joblib.dump(dict(self.metrics_history), metrics_path)
        
        logger.info("="*70)
        logger.info("✅ TRAINING COMPLETE!")
        logger.info("="*70)
        logger.info(f"   Best Val Loss: {best_score:.4f}")
        logger.info(f"   Final Dir Accuracy: {direction_accuracy:.1f}%")
        logger.info(f"   Final Price RMSE: {price_rmse:.2f}")
        
        return {
            'best_val_loss': best_score,
            'final_direction_accuracy': direction_accuracy,
            'final_price_rmse': price_rmse,
            'final_price_r2': price_r2
        }
    
    def predict(self, ticker: str, capital: float = 100000, risk_pct: float = 2.0) -> Dict:
        """
        Make prediction for a single ticker
        """
        try:
            # Load model if not already loaded
            if self.model is None:
                model_path, scaler_path, target_scalers_path, feature_cols_path, _ = self._get_paths()
                
                if not os.path.exists(model_path):
                    return {"error": "Model not trained yet. Please run training first."}
                
                # Load scalers and feature columns
                self.feature_scaler = joblib.load(scaler_path)
                self.target_scalers = joblib.load(target_scalers_path)
                self.feature_cols = joblib.load(feature_cols_path)
                
                # Load model
                checkpoint = torch.load(model_path, map_location=self.device)
                self.model = StockPredictorModel(
                    len(self.feature_cols),
                    hidden_dim=CONFIG['hidden_dim'],
                    dropout=CONFIG['dropout']
                )
                self.model.load_state_dict(checkpoint['model_state_dict'])
                self.model = self.model.to(self.device)
                self.model.eval()
            
            # Fetch data
            query = text("""
                SELECT date, open, high, low, close, volume, adj_close
                FROM nse_stocks
                WHERE ticker = :ticker
                ORDER BY date ASC
            """)
            df = pd.read_sql(query, self.engine, params={'ticker': ticker})
            
            if df.empty or len(df) < 100:
                return {"error": f"Insufficient data for {ticker}"}
            
            # Engineer features
            df = QuickFeatureEngineer.engineer_features(df)
            
            # Prepare sequence
            seq_len = CONFIG['seq_len']
            available_cols = [c for c in self.feature_cols if c in df.columns]
            
            if len(available_cols) < len(self.feature_cols) * 0.8:
                return {"error": "Feature mismatch"}
            
            # Get last sequence
            feat_arr = df[available_cols].values[-seq_len:].astype(np.float32)
            feat_arr = np.nan_to_num(feat_arr, nan=0.0, posinf=0.0, neginf=0.0)
            
            # Scale
            original_shape = feat_arr.shape
            feat_scaled = self.feature_scaler.transform(feat_arr.reshape(-1, original_shape[-1]))
            feat_scaled = feat_scaled.reshape(original_shape)
            feat_scaled = np.clip(feat_scaled, -10, 10)
            
            # Predict
            with torch.no_grad():
                features_tensor = torch.FloatTensor(feat_scaled).unsqueeze(0).to(self.device)
                preds = self.model(features_tensor)
                
                # Get predictions
                price_pred = preds['price'].cpu().numpy()[0, 0]
                direction_logit = preds['direction'].cpu().numpy()[0, 0]
                direction_prob = float(1 / (1 + np.exp(-direction_logit)))  # Apply sigmoid
                volatility_pred = preds['volatility'].cpu().numpy()[0, 0]
                confidence = preds['confidence'].cpu().numpy()[0, 0]
            
            # Inverse scale price prediction
            price_change = self.target_scalers['price'].inverse_transform([[price_pred]])[0, 0]
            
            # Current price
            current_price = float(df['close'].iloc[-1])
            predicted_price = current_price + price_change
            
            # Risk management
            atr = float(df['atr_14'].iloc[-1]) if 'atr_14' in df.columns else current_price * 0.02
            stop_loss = current_price - (2 * atr) if direction_prob > 0.5 else current_price + (2 * atr)
            target = current_price + (3 * atr) if direction_prob > 0.5 else current_price - (3 * atr)
            
            risk_per_share = abs(current_price - stop_loss)
            risk_amount = capital * (risk_pct / 100)
            quantity = int(risk_amount / risk_per_share) if risk_per_share > 0 else 0
            
            # Signal
            if direction_prob > 0.65 and confidence > 0.6:
                signal = "STRONG BUY" if direction_prob > 0.5 else "STRONG SELL"
                signal_strength = "HIGH"
            elif direction_prob > 0.55:
                signal = "BUY" if direction_prob > 0.5 else "SELL"
                signal_strength = "MEDIUM"
            else:
                signal = "HOLD"
                signal_strength = "LOW"
            
            result = {
                'ticker': ticker,
                'timestamp': datetime.now().isoformat(),
                'price_analysis': {
                    'current_price': round(current_price, 2),
                    'predicted_price_5d': round(predicted_price, 2),
                    'expected_change': round(price_change, 2),
                    'expected_change_pct': round((price_change / current_price) * 100, 2)
                },
                'recommendation': {
                    'signal': signal,
                    'signal_strength': signal_strength,
                    'direction_probability': round(direction_prob * 100, 1),
                    'confidence_score': round(confidence * 100, 1)
                },
                'risk_management': {
                    'stop_loss': round(stop_loss, 2),
                    'target_price': round(target, 2),
                    'risk_reward_ratio': round(abs(target - current_price) / abs(stop_loss - current_price), 2) if abs(stop_loss - current_price) > 0 else 0,
                    'suggested_quantity': quantity,
                    'position_size': round(quantity * current_price, 2)
                }
            }
            
            # Track prediction
            self.prediction_tracker.record(ticker, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Prediction error for {ticker}: {e}")
            return {"error": str(e)}
    
    def batch_predict(self, tickers: Optional[List[str]] = None, 
                     min_signal_strength: str = "MEDIUM") -> pd.DataFrame:
        """
        Generate predictions for multiple stocks
        """
        logger.info("="*70)
        logger.info("🔍 BATCH PREDICTION")
        logger.info("="*70)
        
        # Get all tickers if not specified
        if tickers is None:
            query = text("SELECT DISTINCT ticker FROM nse_stocks ORDER BY ticker")
            result = self.engine.execute(query)
            tickers = [row[0] for row in result]
        
        logger.info(f"Generating predictions for {len(tickers)} stocks...")
        
        results = []
        for ticker in tqdm(tickers, desc="Predicting"):
            try:
                pred = self.predict(ticker)
                
                if 'error' not in pred:
                    # Filter by signal strength
                    if min_signal_strength == "HIGH" and pred['recommendation']['signal_strength'] != "HIGH":
                        continue
                    if min_signal_strength == "MEDIUM" and pred['recommendation']['signal_strength'] == "LOW":
                        continue
                    
                    results.append({
                        'ticker': ticker,
                        'signal': pred['recommendation']['signal'],
                        'signal_strength': pred['recommendation']['signal_strength'],
                        'direction_prob': pred['recommendation']['direction_probability'],
                        'confidence': pred['recommendation']['confidence_score'],
                        'current_price': pred['price_analysis']['current_price'],
                        'predicted_price': pred['price_analysis']['predicted_price_5d'],
                        'expected_return_pct': pred['price_analysis']['expected_change_pct'],
                        'rr_ratio': pred['risk_management']['risk_reward_ratio'],
                        'quantity': pred['risk_management']['suggested_quantity']
                    })
            except Exception as e:
                logger.debug(f"Error predicting {ticker}: {e}")
                continue
        
        if not results:
            logger.warning("No predictions generated!")
            return pd.DataFrame()
        
        df = pd.DataFrame(results)
        
        # Sort by expected return
        df = df.sort_values('expected_return_pct', ascending=False)
        
        logger.info(f"✅ Generated {len(df)} predictions")
        
        # Save to CSV
        output_file = f"{METRICS_DIR}/batch_predictions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df.to_csv(output_file, index=False)
        logger.info(f"💾 Saved to {output_file}")
        
        return df


# ==================== COMMAND LINE INTERFACE ====================

def main():
    """Command line interface"""
    
    parser = argparse.ArgumentParser(description='Unified Stock Predictor - OPTIMIZED')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Train command
    train_parser = subparsers.add_parser('train', help='Train the model')
    train_parser.add_argument('--tickers', type=int, default=None, help='Number of tickers (Default: All)')
    train_parser.add_argument('--epochs', type=int, default=100, help='Training epochs')
    train_parser.add_argument('--batch-size', type=int, default=256, help='Batch size')
    train_parser.add_argument('--lr', type=float, default=0.001, help='Learning rate')
    
    # Predict command
    predict_parser = subparsers.add_parser('predict', help='Predict for a stock')
    predict_parser.add_argument('ticker', type=str, help='Stock ticker')
    predict_parser.add_argument('--capital', type=float, default=100000, help='Capital')
    predict_parser.add_argument('--risk', type=float, default=2.0, help='Risk %')
    
    # Batch predict command
    batch_parser = subparsers.add_parser('batch-predict', help='Predict for multiple stocks')
    batch_parser.add_argument('--tickers', nargs='+', help='List of tickers')
    batch_parser.add_argument('--min-strength', choices=['LOW', 'MEDIUM', 'HIGH'], 
                            default='MEDIUM', help='Minimum signal strength')
    
    args = parser.parse_args()
    
    # Initialize predictor
    predictor = UnifiedStockPredictor()
    
    if args.command == 'train':
        logger.info("\n🚀 Starting Training on ALL Available Stocks\n")
        try:
            metrics = predictor.train(
                max_tickers=args.tickers,
                epochs=args.epochs,
                batch_size=args.batch_size,
                learning_rate=args.lr
            )
            logger.info(f"\n✅ Training complete! Metrics: {metrics}\n")
            
            # INTERACTIVE PREDICTION LOOP
            print("\n" + "="*50)
            print("   INTERACTIVE PREDICTION MODE")
            print("="*50)
            print("Type a stock ticker (e.g., RELIANCE) to predict, or 'exit' to quit.\n")
            
            while True:
                user_ticker = input(">> Enter Stock Ticker: ").strip().upper()
                if user_ticker in ['EXIT', 'QUIT', 'NO']:
                    print("Exiting. Happy Trading!")
                    break
                
                if not user_ticker:
                    continue
                    
                try:
                    pred = predictor.predict(user_ticker)
                    if 'error' in pred:
                        print(f"❌ Error: {pred['error']}")
                    else:
                        print(f"\n📊 REPORT: {user_ticker}")
                        print(f"   Signal: {pred['recommendation']['signal']} ({pred['recommendation']['signal_strength']})")
                        print(f"   Current Price: {pred['price_analysis']['current_price']}")
                        print(f"   Target Price (5d): {pred['price_analysis']['predicted_price_5d']}")
                        print(f"   Expected Return: {pred['price_analysis']['expected_change_pct']}%\n")
                except Exception as e:
                    print(f"❌ Error occurred: {e}")

        except Exception as e:
            logger.error(f"Training Failed: {e}")
    
    elif args.command == 'predict':
        logger.info(f"\n🎯 Predicting {args.ticker}\n")
        result = predictor.predict(args.ticker, capital=args.capital, risk_pct=args.risk)
        
        if 'error' in result:
            logger.error(f"❌ {result['error']}")
        else:
            logger.info("\n" + "="*70)
            logger.info(f"📊 PREDICTION: {args.ticker}")
            logger.info("="*70)
            logger.info(f"\nSignal: {result['recommendation']['signal']} ({result['recommendation']['signal_strength']})")
            logger.info(f"Direction Probability: {result['recommendation']['direction_probability']}%")
            logger.info(f"Confidence: {result['recommendation']['confidence_score']}%")
            logger.info(f"\nCurrent Price: ₹{result['price_analysis']['current_price']}")
            logger.info(f"Predicted Price (5d): ₹{result['price_analysis']['predicted_price_5d']}")
            logger.info(f"Expected Return: {result['price_analysis']['expected_change_pct']}%")
            logger.info(f"\nStop Loss: ₹{result['risk_management']['stop_loss']}")
            logger.info(f"Target: ₹{result['risk_management']['target_price']}")
            logger.info(f"Risk/Reward: 1:{result['risk_management']['risk_reward_ratio']:.1f}")
            logger.info(f"Suggested Quantity: {result['risk_management']['suggested_quantity']} shares")
            logger.info("="*70 + "\n")
    
    elif args.command == 'batch-predict':
        logger.info("\n🔍 Batch Prediction\n")
        df = predictor.batch_predict(
            tickers=args.tickers,
            min_signal_strength=args.min_strength
        )
        
        if not df.empty:
            logger.info("\n" + "="*70)
            logger.info("📊 TOP PREDICTIONS")
            logger.info("="*70)
            logger.info(f"\n{df.head(20).to_string()}\n")
    
    else:
        # Default behavior: Train on ALL and then enter interactive mode
        logger.info("\n🚀 STARTING DEFAULT MODE: TRAINING ON ALL STOCKS\n")
        
        predictor = UnifiedStockPredictor()
        metrics = predictor.train(max_tickers=None, epochs=100)
        
        print("\n" + "="*50)
        print("   INTERACTIVE PREDICTION MODE")
        print("="*50)
        print("Type a stock ticker (e.g., RELIANCE) to predict, or 'exit' to quit.\n")
        
        while True:
            user_ticker = input(">> Enter Stock Ticker: ").strip().upper()
            if user_ticker in ['EXIT', 'QUIT', 'NO']:
                break
            
            if not user_ticker:
                continue
                
            try:
                pred = predictor.predict(user_ticker)
                if 'error' in pred:
                    print(f"❌ Error: {pred['error']}")
                else:
                    print(f"\n📊 REPORT: {user_ticker}")
                    print(f"   Signal: {pred['recommendation']['signal']} ({pred['recommendation']['signal_strength']})")
                    print(f"   Price: {pred['price_analysis']['current_price']} -> {pred['price_analysis']['predicted_price_5d']}")
                    print(f"   Return: {pred['price_analysis']['expected_change_pct']}%\n")
            except Exception as e:
                print(f"❌ Error occurred: {e}")

if __name__ == "__main__":
    main()
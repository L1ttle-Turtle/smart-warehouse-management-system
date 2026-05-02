import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { ConfigProvider, App as AntApp } from 'antd';

import App from './App';
import { AuthProvider } from './auth/AuthContext';
import 'antd/dist/reset.css';
import './index.css';

const theme = {
  token: {
    colorPrimary: '#7c3aed',
    colorInfo: '#7c3aed',
    colorSuccess: '#10b981',
    colorWarning: '#f59e0b',
    colorError: '#ef4444',
    colorText: '#18181b',
    colorTextSecondary: '#71717a',
    colorBgLayout: '#f7f4ff',
    colorBgContainer: '#ffffff',
    borderRadius: 16,
    fontFamily: '"Plus Jakarta Sans", sans-serif',
    boxShadow: '0 18px 50px rgba(76, 29, 149, 0.12)',
  },
  components: {
    Button: {
      borderRadius: 14,
      controlHeight: 40,
    },
    Card: {
      borderRadiusLG: 24,
    },
    Table: {
      borderColor: 'rgba(124, 58, 237, 0.1)',
      headerBg: 'rgba(250, 245, 255, 0.85)',
      headerColor: '#3b0764',
    },
    Input: {
      borderRadius: 14,
    },
    Select: {
      borderRadius: 14,
    },
  },
};

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ConfigProvider theme={theme}>
      <AntApp>
        <BrowserRouter>
          <AuthProvider>
            <App />
          </AuthProvider>
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  </React.StrictMode>,
);

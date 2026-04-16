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
    colorPrimary: '#1f6f5f',
    colorInfo: '#1f6f5f',
    colorSuccess: '#2d8f78',
    colorWarning: '#d49727',
    colorError: '#cc5b45',
    borderRadius: 18,
    fontFamily: '"IBM Plex Sans", sans-serif',
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

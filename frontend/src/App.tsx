import { BrowserRouter } from 'react-router-dom';
import AppRoutes from './routes';
import './styles/global.css';

export default function App() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}


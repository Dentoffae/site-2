import { FloatingOrbs } from "./components/FloatingOrbs";
import { LeadForm } from "./components/LeadForm";
import "./styles/global.css";

export default function App() {
  return (
    <div className="app-root">
      <FloatingOrbs />
      <a className="skip-link" href="#lead-form">
        К форме
      </a>
      <div className="layout">
        <header className="hero">
          <p className="hero-eyebrow">Autobizlab</p>
          <h1>Заявка на услуги</h1>
          <p>
            Оставьте контакты и задачу — данные уходят на защищённый контур через Nginx. К заявке
            добавляются служебные метрики (браузер, экран, UTM, сессия) для аналитики лида.
          </p>
        </header>
        <LeadForm />
        <footer className="site-footer">
          Технические метрики собираются в вашем браузере и отправляются одним запросом вместе с
          формой на <code>/api/v1/leads</code>. Данные не уходят на сторонние аналитические сервисы.
        </footer>
      </div>
    </div>
  );
}

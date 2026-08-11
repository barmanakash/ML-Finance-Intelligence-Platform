import { Search, Bell, User } from 'lucide-react';

export function Header() {
  return (
    <header className="header glass">
      <div className="header-search">
        <Search className="search-icon text-muted" size={18} />
        <input 
          type="text" 
          placeholder="Search transactions, insights..." 
          className="search-input"
        />
      </div>
      
      <div className="header-actions">
        <button className="icon-btn">
          <Bell size={20} />
          <span className="badge">3</span>
        </button>
        <button className="user-menu-btn">
          <div className="avatar">
            <User size={18} />
          </div>
        </button>
      </div>
    </header>
  );
}

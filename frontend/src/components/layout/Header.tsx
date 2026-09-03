"use client";

import { Search, LogOut, User as UserIcon } from 'lucide-react';
import { useAuth } from '@/lib/auth';

export function Header() {
  const { user, logout } = useAuth();

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
        {user && <span className="header-username">{user.full_name}</span>}
        <button className="icon-btn" onClick={logout} title="Log out">
          <LogOut size={18} />
        </button>
        <button className="user-menu-btn">
          <div className="avatar">
            <UserIcon size={18} />
          </div>
        </button>
      </div>
    </header>
  );
}

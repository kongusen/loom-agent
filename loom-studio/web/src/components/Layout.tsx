
import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { Activity, GitGraph, Clock } from 'lucide-react';
import './Layout.css';

const Layout: React.FC = () => {
  return (
    <div className="layout">
      <header className="header">
        <div className="logo">Loom Studio</div>
        <nav className="nav">
          <NavLink to="/" className={({ isActive }) => isActive ? 'active' : ''}>
            <Activity size={18} /> Dashboard
          </NavLink>
          <NavLink to="/topology" className={({ isActive }) => isActive ? 'active' : ''}>
            <GitGraph size={18} /> Topology
          </NavLink>
          <NavLink to="/timeline" className={({ isActive }) => isActive ? 'active' : ''}>
            <Clock size={18} /> Timeline
          </NavLink>
        </nav>
      </header>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
};

export default Layout;

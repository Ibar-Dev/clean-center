import { Routes } from '@angular/router';

import { adminGuard } from './core/admin.guard';
import { AdminLoginPageComponent } from './features/admin/login/admin-login-page.component';
import { AdminLayoutComponent } from './features/admin/admin-layout.component';
import { AdminProductsPageComponent } from './features/admin/products/admin-products-page.component';
import { AdminReservationsPageComponent } from './features/admin/reservations/admin-reservations-page.component';
import { CartPageComponent } from './features/cart/cart-page.component';
import { CatalogPageComponent } from './features/catalog/catalog-page.component';
import { CheckoutPageComponent } from './features/checkout/checkout-page.component';
import { ConfirmationPageComponent } from './features/confirmation/confirmation-page.component';
import { LookupPageComponent } from './features/lookup/lookup-page.component';

export const routes: Routes = [
  {
    path: '',
    component: CatalogPageComponent,
    title: 'Clean Center · Catálogo Click & Collect',
  },
  {
    path: 'carrito',
    component: CartPageComponent,
    title: 'Carrito · Clean Center',
  },
  {
    path: 'checkout',
    component: CheckoutPageComponent,
    title: 'Datos de la reserva · Clean Center',
  },
  {
    path: 'confirmacion/:code',
    component: ConfirmationPageComponent,
    title: 'Reserva confirmada · Clean Center',
  },
  {
    path: 'consulta',
    component: LookupPageComponent,
    data: { mode: 'consulta' },
    title: 'Consultar reserva · Clean Center',
  },
  {
    path: 'arrepentimiento',
    component: LookupPageComponent,
    data: { mode: 'arrepentimiento' },
    title: 'Botón de Arrepentimiento · Clean Center',
  },
  {
    path: 'admin/login',
    component: AdminLoginPageComponent,
    title: 'Acceso administración · Clean Center',
  },
  {
    path: 'admin',
    component: AdminLayoutComponent,
    canActivate: [adminGuard],
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'reservas' },
      {
        path: 'reservas',
        component: AdminReservationsPageComponent,
        title: 'Reservas · Panel Clean Center',
      },
      {
        path: 'productos',
        component: AdminProductsPageComponent,
        title: 'Productos · Panel Clean Center',
      },
    ],
  },
  { path: '**', redirectTo: '' },
];

import DashboardClient from './dashboard-client';
import {loadBootstrap} from '../lib/bootstrap.server';
// Files from the pinned snapshot only; no live network dependency during build.
export default async function Page() {
  return <DashboardClient bootstrap={await loadBootstrap()} />;
}

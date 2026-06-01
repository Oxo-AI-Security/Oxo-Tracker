import type { ConnectorListItem, CurrentUser } from '../types/connector'

export function canEditConnector(connector: ConnectorListItem, currentUser: CurrentUser) {
  return connector.source === 'user-created' && connector.ownerId === currentUser.id
}

export function canDeleteConnector(connector: ConnectorListItem, currentUser: CurrentUser) {
  return connector.source === 'user-created' && connector.ownerId === currentUser.id && Boolean(connector.config.id)
}

"""路由聚合：各业务域 APIRouter。"""
from routes import config as config_routes
from routes import wardrobe as wardrobe_routes
from routes import user as user_routes
from routes import tryon as tryon_routes
from routes import outfits as outfits_routes
from routes import auth as auth_routes
from routes import security as security_routes
from routes import admin as admin_routes

routers = [
    config_routes.router,
    wardrobe_routes.router,
    user_routes.router,
    tryon_routes.router,
    outfits_routes.router,
    auth_routes.router,
    security_routes.router,
    admin_routes.router,
]

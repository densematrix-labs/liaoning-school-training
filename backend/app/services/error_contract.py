"""Stable public errors; never echo submitted credentials or business input."""
import uuid
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

CODES={500:'INTERNAL_ERROR',400:'INPUT_INVALID',401:'AUTH_REQUIRED',403:'ACCESS_DENIED',404:'RESOURCE_NOT_FOUND',409:'STATE_CONFLICT',422:'PARAMETER_INVALID',429:'RATE_LIMITED',502:'UPSTREAM_FAILURE',503:'SERVICE_UNAVAILABLE'}

def error_response(status, detail, request_id=None, headers=None):
    return JSONResponse(status_code=status,headers=headers,content={'status':'error','code':CODES.get(status,'INTERNAL_ERROR'),'message':detail if isinstance(detail,str) else '请求参数校验失败','detail':detail,'request_id':request_id or uuid.uuid4().hex})

def install_errors(app):
    @app.exception_handler(HTTPException)
    async def http_error(request,exc):
        return error_response(exc.status_code,exc.detail,getattr(request.state,'request_id',None),exc.headers)
    @app.exception_handler(RequestValidationError)
    async def validation_error(request,exc):
        details=[{'loc':list(e['loc']),'msg':e['msg'],'type':e['type']} for e in exc.errors()]
        return error_response(422,details,getattr(request.state,'request_id',None))
    @app.exception_handler(Exception)
    async def internal_error(request,exc):
        return error_response(500,'服务内部异常，请使用请求ID联系管理员',getattr(request.state,'request_id',None))
    original_openapi=app.openapi
    def openapi():
        schema=original_openapi()
        schema.setdefault('components',{}).setdefault('schemas',{})['BusinessError']={'type':'object','required':['status','code','message','detail','request_id'],'properties':{'status':{'type':'string','enum':['error']},'code':{'type':'string','description':'统一业务异常编码，不等同HTTP状态码','enum':list(CODES.values())+['INTERNAL_ERROR']},'message':{'type':'string'},'detail':{'description':'错误原因或不含input原值的字段定位列表'},'request_id':{'type':'string','description':'请求追踪ID，与X-Request-ID一致'}}}
        for path in schema.get('paths',{}).values():
            for operation in path.values():
                if not isinstance(operation,dict):continue
                for status in (401,403,422):
                    operation.setdefault('responses',{})[str(status)]={'description':CODES[status],'content':{'application/json':{'schema':{'$ref':'#/components/schemas/BusinessError'}}}}
        return schema
    app.openapi=openapi

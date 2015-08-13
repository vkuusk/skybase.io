class SkyBaseError(Exception):
    pass

class SkyBaseRestAPIError(SkyBaseError):
    pass

class SkyBaseUserAuthorizationError(SkyBaseError):
    pass

class SkyBaseDeployError(SkyBaseError):
    pass

class SkyBasePlanetError(SkyBaseError):
    pass

class SkyBaseNotImplementedError(SkyBaseError):
    pass

class SkyBaseConfigurationError(SkyBaseError):
    pass

class SkyBaseTaskValidationError(SkyBaseError):
    pass

class SkyBaseTaskRoutingError(SkyBaseError):
    pass

class SkyBaseRoleNotFoundError(SkyBaseError):
    pass

class SkyBaseDeleteUserError(SkyBaseError):
    pass

class SkyBaseUserIdNotFoundError(SkyBaseError):
    pass

class SkyBaseAuthenticationError(SkyBaseError):
    pass

class SkyBaseTimeOutError(SkyBaseError):
    pass

class SkyBaseResponseError(SkyBaseError):
    pass

class SkyBaseValidationError(SkyBaseError):
    pass

class SkyBasePresubmitCheckError(SkyBaseError):
    pass

class StateDBError(SkyBaseError):
    pass

class StateDBRecordNotFoundError(StateDBError):
    pass
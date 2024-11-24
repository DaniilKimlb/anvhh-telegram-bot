from dotenv import load_dotenv
import os
load_dotenv()
class BaseConfig:
  def getDatabaseUrl(self):
    return os.getenv("DATABASE_URL")
  
  def getBotToken(self):
    return  os.getenv("BOT_TOKEN")
  
  def getEncryptionKey(self):
    return os.getenv('ENCRYPTION_KEY', '')

  def getCLientId(self):
    return os.getenv('CLIENT_ID', '')

  def geClientSecret(self):
    return os.getenv('CLIENT_SECRET', '')

  def getBaseUrl(self):
    return os.getenv('BASE_URL', '')
  
  def getUserAgent(self):
    return os.getenv('USER_AGENT', '')
  
  def getRedirectUri(self):
    return os.getenv('REDIRECT_URI', '')
  
  def getAuthUrl(self, chat_id):
    return f"https://hh.kz/oauth/authorize?response_type=code&client_id={self.getCLientId()}&redirect_uri={self.getRedirectUri()}/&state={chat_id}"
  
  
  
base_config = BaseConfig()

   

log_level                :info
log_location             STDOUT
node_name                "#{ENV['CHEF_NODE_NAME']}"
client_key               "#{ENV['CHEF_CREDS_PATH']}/#{ENV['CHEF_CLIENT_KEY']}"
validation_client_name   "#{ENV['CHEF_VALIDATION_CLIENT_NAME']}"
validation_key           "#{ENV['CHEF_CREDS_PATH']}/#{ENV['CHEF_VALIDATION_KEY']}"
chef_server_url          "#{ENV['CHEF_SERVER_URL']}"
cache_type               'BasicFile'
cache_options( :path => "#{ENV['HOME']}/.chef/checksums" )
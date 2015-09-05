log_level                :info
log_location             STDOUT
node_name                "skybase"
client_key               "#{ENV['CHEF_CREDS_PATH']}/skybase-client-chef-dev-aws-us-west-1.pem"
validation_client_name   "skytest-validator"
validation_key           "#{ENV['CHEF_CREDS_PATH']}/skytest-validator-sky-chef-dev-aws-us-west-1.pem"
chef_server_url          "https://your.chef.host.here.com"
cache_type               'BasicFile'
cache_options( :path => "#{ENV['HOME']}/.chef/checksums" )

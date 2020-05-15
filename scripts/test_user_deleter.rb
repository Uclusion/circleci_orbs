#!/usr/bin/env ruby
# Simple script to nuke test users from a cognito idp pool
require 'optparse'
require 'json'

options = {}
OptionParser.new do |opts|
  opts.banner = "Usage: test_user_deleter.rb --poolId=<yourpoolid>"
  opts.on("-p", "--poolId POOLID", "POOLID is required") do |p|
    options[:poolId] = p
  end
end.parse!


def is_test_user(email)
  isTuser = email.start_with?('tuser+') && email.end_with?('@uclusion.com')
  isUclude = email.end_with?('@uclude.com')
  return isTuser || isUclude
end


poolId = options[:poolId]

users_response_string = `aws cognito-idp list-users --user-pool-id=#{poolId}`
users_response = JSON.parse(users_response_string)
users = users_response['Users']
puts users.size
users.each do |user|
  attributes = user['Attributes']
  id = user['Username']
  email_attr = attributes.find {|attr| attr['Name'] == 'email'}
  email = email_attr['Value']
#  puts(email)
  isTest = is_test_user(email)
  if isTest then
    puts("Deleting user #{email} with user name #{id}")
    command = "aws cognito-idp admin-delete-user --user-pool-id=#{poolId} --username=#{id}"
    puts(command)
    `#{command}`
  end
end




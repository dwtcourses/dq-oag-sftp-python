FROM centos:centos7

ENV RDS_HOST='postgresql'
ENV RDS_DATABASE='foo'
ENV RDS_USERNAME='root'
ENV PGPASSWORD='foobar'
ENV RDS_TABLE='bar'

RUN yum install postgresql-server -y

CMD psql -h $RDS_HOST -p 5432 -d $RDS_DATABASE -U $RDS_USERNAME -c "CREATE TABLE $RDS_TABLE(filename VARCHAR(50) UNIQUE NOT NULL)"

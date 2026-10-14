
pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main',
                    url: 'https://github.com/Vamsi-Vyas/medicare-devops.git'
            }
        }

        stage('Validate Application') {
            steps {
                sh 'test -s app/index.html'
                sh 'grep -q "MediCare" app/index.html'
                echo 'Application validation passed'
            }
        }

        stage('Security Scan - Application') {
            steps {
                sh '''
                    set -eu
                    trivy fs --scanners vuln,secret \
                        --severity HIGH,CRITICAL \
                        --exit-code 1 .
                '''
            }
        }

        stage('Security Scan - Dockerfile') {
            steps {
                sh '''
                    set -eu
                    trivy config --severity HIGH,CRITICAL \
                        --exit-code 1 Dockerfile
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                sh 'docker build -t medicare-devops:${BUILD_NUMBER} .'
            }
        }

        stage('Smoke Test') {
            steps {
                sh '''
                    set -eu
                    NAME=medicare-test-${BUILD_NUMBER}
                    PORT=18081

docker run -d --name "$NAME" -p 127.0.0.1:$PORT:8080 medicare-devops:${BUILD_NUMBER}
                    trap 'docker rm -f "$NAME" >/dev/null 2>&1 || true' EXIT

                    for i in $(seq 1 20); do
                        if curl -fsS http://127.0.0.1:$PORT/ \
                            | grep -q 'MediCare'; then
                            echo 'Smoke test passed'
                            exit 0
                        fi
                        sleep 2
                    done

                    exit 1
                '''
            }
        }
    }

    post {
        success {
            echo 'CI/CD and security checks completed successfully'
        }
        failure {
            echo 'Pipeline failed. Check Console Output for the failed stage.'
        }
    }
}

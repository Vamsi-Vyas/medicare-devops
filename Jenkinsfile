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
                    docker rm -f "$NAME" >/dev/null 2>&1 || true
                    docker run -d --name "$NAME" -p 127.0.0.1:$PORT:80 medicare-devops:${BUILD_NUMBER}
                    trap 'docker rm -f "$NAME" >/dev/null 2>&1 || true' EXIT
                    for i in $(seq 1 20); do
                        if curl -fsS http://127.0.0.1:$PORT/ | grep -q 'MediCare'; then
                            echo 'Smoke test passed'
                            exit 0
                        fi
                        sleep 2
                    done
                    echo 'Smoke test failed'
                    exit 1
                '''
            }
        }
    }

    post {
        success {
            echo 'CI pipeline completed successfully'
        }
        failure {
            echo 'CI pipeline failed. Check the console output.'
        }
    }
}
